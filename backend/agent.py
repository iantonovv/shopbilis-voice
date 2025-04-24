import logging
import random
import asyncio
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from livekit import api
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    JobContext,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
)
from livekit.agents.job import get_job_context
from livekit.agents.llm import function_tool
from livekit.plugins import openai
from openai.types.beta.realtime.session import TurnDetection

# uncomment to enable Krisp BVC noise cancellation, currently supported on Linux and MacOS
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("multi-agent")

load_dotenv()

common_instructions = (
    "You are ShopBilis' customer service support that interacts with the user via voice. "
    "You are accommodating and should try to answer as concisely as possible while remaining polite. "
    "ALWAYS Match the customer's language preference (Tagalog/English or a mix of both)."
)


@dataclass
class CustomerData:
    escalation: bool = False
    concern: Optional[str] = None
    tracking_number: Optional[str] = None
    order_status: Optional[str] = None


class Tier1And2Agent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"""{common_instructions}
            Your name is Bilis (In tagalog accent). You are ShopBilis' friendly customer support agent handling Tier 1-2 support.
            Respond in under 1.5 seconds. Match customer's language (Tagalog/English). Start introduction with English.
            
            Tier 1 Tasks:
            - Answer basic order tracking inquiries (e.g., "Nasaan na ang order ko?")
            - For tracking inquiries, ask for tracking number and provide package status
            
            Tier 2 Tasks:
            - Handle simple return and refund policy questions (e.g., "Paano magpa-refund?")
            - For refund policy questions, inform customers you need to look up the information
            
            If the customer:
            - Uses angry language
            - Threatens to cancel their order
            - Has complex issues beyond basic tracking or refund policies
            - Uses profanity or appears very upset
            
            Then escalate to the Tier 3 agent by using the escalation_needed function.
            """
        )

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        self.session.generate_reply()

    @function_tool
    async def lookup_order_status(self, context: RunContext[CustomerData], tracking_number: str):
        """Look up the status of an order based on tracking number.

        Args:
            tracking_number: The tracking number of the order to look up
        """
        # Simulate order status lookup
        context.userdata.tracking_number = tracking_number
        
        # Generate random status
        statuses = [
            "Your package is out for delivery today. Expect calls or texts from our delivery partners soon.",
            "Your order is currently in transit and should arrive within 1-2 business days.",
            "Your package has reached our distribution center and will be dispatched for delivery soon.",
            "Your order is being prepared for shipping and will leave our warehouse today."
        ]
        
        context.userdata.order_status = random.choice(statuses)
        
        return context.userdata.order_status

    @function_tool
    async def lookup_refund_policy(self, context: RunContext[CustomerData]):
        """Look up refund policy information for the customer.
        This simulates a RAG (Retrieval Augmented Generation) process.
        """
        # Tell the customer we're looking up the information
        self.session.interrupt()
        await self.session.generate_reply(
            instructions="Tell the customer you're looking up the refund information. Say something like 'Sandali lang, hahanapin ko lang iyong information about refunds.'",
            allow_interruptions=False
        )
        
        # Simulate delay for information retrieval
        await asyncio.sleep(3)
        
        refund_policy = (
            "Para sa refund process ng ShopBilis, may 7-day return policy kami mula sa pag-deliver. "
            "Kailangan i-upload ang proof at reason sa ShopBilis app o website. "
            "Pagkatapos ma-approve, 3-5 business days bago marefund sa original payment method. "
            "Para sa damaged items, kailangan ng photo evidence. "
            "Maaari ring mag-request ng replacement kaysa refund kung available pa ang item."
        )
        
        return refund_policy

    @function_tool
    async def escalation_needed(
        self,
        context: RunContext[CustomerData],
        concern: str
    ):
        """Called when the customer needs escalation to Tier 3 support.

        Args:
            concern: what the customer's concern is
        """
        context.userdata.escalation = True
        context.userdata.concern = concern

        tier3_agent = Tier3Agent(context.userdata.concern)

        logger.info(
            "Escalating to Tier 3 agent with concern: %s"
        )
        return tier3_agent, "Escalate the situation"


class Tier3Agent(Agent):
    def __init__(self, concern: str, *, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(
            instructions=f"""{common_instructions}
            You are Mario, ShopBilis' senior customer support specialist handling Tier 3 issues. Respond in under 1.5 seconds. Match customer's language (Tagalog/English). 
            The customer concern being escalated is: {concern}
            
            You handle complex cases like:
            - Order cancellations after shipment
            - Payment disputes
            - Serious complaints
            - Angry or upset customers
            
            You have authority to approve refunds up to ₱25,000.
            Be empathetic but professional. Always start by:
            1. Introducing yourself as the senior specialist
            2. Acknowledging their concern
            3. Apologizing for any inconvenience
            4. Offering concrete solutions
            
            Use a calm, reassuring tone even if the customer is upset.
            """,
            # Using a different voice for the Tier 3 agent
            llm=openai.realtime.RealtimeModel(
                voice="ballad",
                turn_detection=TurnDetection(
                    type="semantic_vad",
                    eagerness="high",
                    create_response=True,
                    interrupt_response=False,
                )
            ),
            tts=None,
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        # when the agent is added to the session, we'll initiate the conversation
        self.session.generate_reply()

    @function_tool
    async def process_order_cancellation(self, context: RunContext[CustomerData], reason: str):
        """Process an order cancellation request.

        Args:
            reason: The reason for cancellation
        """
        # Simulate processing time
        await asyncio.sleep(2)
        
        return (
            f"I've processed your cancellation request due to: {reason}. "
            "Your order has been successfully cancelled, and a full refund will be issued to your original payment method within 3-5 business days. "
            "You'll receive a confirmation email shortly with all the details."
        )

    @function_tool
    async def offer_compensation(self, context: RunContext[CustomerData], amount: int, reason: str):
        """Offer compensation to the customer for their inconvenience.

        Args:
            amount: Amount in PHP to offer as compensation
            reason: Reason for offering compensation
        """
        return f"As a goodwill gesture for the {reason}, I'd like to offer you ₱{amount} in ShopBilis credits that will be added to your account immediately."

    @function_tool
    async def conversation_finished(self, context: RunContext[CustomerData]):
        """When you are finished handling the customer (and the user confirms they don't
        want anything else), call this function to end the conversation."""
        # interrupt any existing generation
        self.session.interrupt()

        # generate a goodbye message and hang up
        await self.session.generate_reply(
            instructions="Thank the customer for their patience, apologize again for any inconvenience, and say goodbye warmly.",
            allow_interruptions=False
        )

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession[CustomerData](
        llm=openai.realtime.RealtimeModel(
            voice="coral",
            turn_detection=TurnDetection(
                type="semantic_vad",
                eagerness="high",
                create_response=True,
                interrupt_response=False,
            )),
        userdata=CustomerData(),
    )


    await session.start(
        agent=Tier1And2Agent(),
        room=ctx.room,
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))