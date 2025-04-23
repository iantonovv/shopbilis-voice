from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent
from livekit.plugins import openai
from openai.types.beta.realtime.session import TurnDetection
import random
import asyncio
import re

load_dotenv()

class EscalationState:
    value = False

class ShopBilisTier1and2Agent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
            You are BILIS, ShopBilis' friendly customer support agent handling Tier 1-2 support.
            Respond in under 1.5 seconds. Match customer's language (Tagalog/English).
            You will handle basic tasks like basic information about the company (it's a courier business), and handle simple return and refund policies
            Escalate to Tier 3 if customer is angry or mentions: order cancellation after shipment, or needs manager attention
            """
        )
        self.asked_for_tracking = False

    async def handle_message(self, message: str) -> str:
        if self._should_escalate(message):
            EscalationState.value = True
            return "Ipapasa ko po kayo sa aming senior agent para mas makatulong sa inyo. Sandali lang po."
        
        return await self._handle_normal_query(message)
        
    async def _handle_normal_query(self, message: str) -> str:
        # Handle order tracking (Tier 1)
        if self._is_order_tracking_query(message):
            tracking_number = self._extract_tracking_number(message)
            if tracking_number:
                return await self._get_order_status(tracking_number)
            else:
                self.asked_for_tracking = True
                return "Pakibigay po ang inyong tracking number para macheck ko ang status ng order niyo."
        
        # If we previously asked for tracking number
        if self.asked_for_tracking:
            tracking_number = self._extract_tracking_number(message)
            if tracking_number:
                return await self._get_order_status(tracking_number)
            self.asked_for_tracking = False
        
        # Handle refund queries (Tier 2)
        if self._is_refund_query(message):
            return await self._provide_refund_information()
        
        # Default response
        return "Ano pa pong maitutulong ko sa inyo? Pwede kong tulungan sa pag-track ng order o kaya naman sa mga katanungan tungkol sa returns at refunds."

    def _should_escalate(self, message: str) -> bool:
        message_lower = message.lower()
        escalation_terms = [
            "hayop", "gago", "cancel", "kansel", "dispute", 
            "manager", "supervisor", "reklamo", "complaint",
            "refund", "ibalik", "pera", "bayad", "return", "isauli", "palit",
            "cancel order", "order cancellation", "payment dispute"
        ]
        excessive_punctuation = len(re.findall(r'[!?]', message)) > 2
        
        return any(term in message_lower for term in escalation_terms) or excessive_punctuation

    def _is_order_tracking_query(self, message: str) -> bool:
        tracking_keywords = ["track", "nasaan", "saan", "order", "delivery", "status"]
        return any(keyword in message.lower() for keyword in tracking_keywords)

    def _extract_tracking_number(self, message: str) -> str:
        sb_pattern = re.search(r'SB-\d+', message)
        if sb_pattern:
            return sb_pattern.group(0)
        number_pattern = re.search(r'\d{8,}', message)
        return number_pattern.group(0) if number_pattern else None

    async def _get_order_status(self, tracking_number: str) -> str:
        await asyncio.sleep(0.2)  # Simulate lookup
        statuses = [
            f"Ang order niyo po ({tracking_number}) ay OUT FOR DELIVERY na ngayong araw.",
            f"Good news! Ang order niyo ({tracking_number}) ay TO SHIP at ide-deliver within 24-48 hours.",
            f"DELIVERED na po ang order niyo ({tracking_number}) kaninang 2:30PM.",
            f"Ang order niyo po ({tracking_number}) ay PREPARING FOR SHIPMENT.",
            f"Na-process na po ang order niyo ({tracking_number}) at nasa SORTING FACILITY namin ngayon."
        ]
        return random.choice(statuses)

    def _is_refund_query(self, message: str) -> bool:
        refund_keywords = ["refund", "ibalik", "pera", "bayad", "return", "isauli", "palit"]
        return any(keyword in message.lower() for keyword in refund_keywords)

    async def _provide_refund_information(self) -> str:
        await asyncio.sleep(0.5)
        return "Para sa refund po, kailangan i-report ang issue within 7 days ng delivery. Pwede po kayong mag-submit ng request sa ShopBilis app."

class ShopBilisTier3Agent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
            You are MARIA, ShopBilis' senior customer support specialist handling Tier 3 issues.
            You handle complex cases like order cancellations after shipment, payment disputes, 
            and serious complaints. You have authority to approve refunds up to ₱25,000.
            Be empathetic but professional. Always start by greeting the customer and 
            acknowledging their concern before offering solutions.
            """
        )
        self.case_number = f"SB-{random.randint(100000, 999999)}"
        self.first_message = True

    async def handle_message(self, message: str) -> str:
        if self.first_message:
            self.first_message = False
            return self._generate_greeting(message)
        
        if any(word in message.lower() for word in ["ok", "sige", "yes", "oo", "ayos", "salamat"]):
            return self._generate_positive_closing()
        return self._generate_solution(message)

    def _generate_greeting(self, message: str) -> str:
        if any(word in message.lower() for word in ["cancel", "kansel"]):
            return (f"Magandang araw po! Ako si Maria, senior specialist ng ShopBilis. "
                    f"Case #{self.case_number} po ang reference natin. Naiintindihan ko po ang inyong "
                    "concern tungkol sa cancellation. Maaari po nating i-arrange ang return pickup.")
            
        elif any(word in message.lower() for word in ["bayad", "payment"]):
            return (f"Magandang araw po! Ako si Maria, senior specialist ng ShopBilis. "
                    f"Case #{self.case_number} po ang reference natin. Tungkol po sa payment concern, "
                    "ive-verify ko agad ang transaction.")
            
        return (f"Magandang araw po! Ako si Maria, senior specialist ng ShopBilis. "
                f"Case #{self.case_number} po ang reference natin. Humihingi ako ng paumanhin "
                "sa naging karanasan niyo. Paano ko po kayo matutulungan?")

    def _generate_positive_closing(self) -> str:
        return (f"Maraming salamat po! Na-process na po ang resolution natin. "
                f"Case #{self.case_number} po ang reference niyo. Makakatanggap po kayo "
                "ng email confirmation within 24 hours.")

    def _generate_solution(self, message: str) -> str:
        return (f"Para sa Case #{self.case_number}, ano pong specific na resolution ang "
                "mas gusto niyo? Bilang senior specialist, may authority po akong magbigay "
                "ng personalized na solusyon para sa inyo.")

class ShopBilisAgentManager:
    def __init__(self):
        self.tier1_2_agent = ShopBilisTier1and2Agent()
        self.tier3_agent = None
        self.current_agent = self.tier1_2_agent
        self.session = None

    async def handle_message(self, ctx: agents.JobContext, message: str) -> str:
        if EscalationState.value and not isinstance(self.current_agent, ShopBilisTier3Agent):
            await self._escalate_to_tier3(ctx)
        
        response = await self.current_agent.handle_message(message)
        
        if "Ipapasa ko po kayo" in response:
            EscalationState.value = True
            await self._escalate_to_tier3(ctx)
        
        return response

    async def _escalate_to_tier3(self, ctx: agents.JobContext):
        print("--- ESCALATING TO TIER 3 AGENT ---")
        if self.session:
            await self.session.close()
        
        self.tier3_agent = ShopBilisTier3Agent()
        self.current_agent = self.tier3_agent
        
        self.session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                voice="nova",
                turn_detection=TurnDetection(
                    type="semantic_vad",
                    eagerness="medium",
                    create_response=True,
                    interrupt_response=True,
                ),
            )
        )
        
        await self.session.start(
            room=ctx.room,
            agent=self.current_agent
        )
        
        await self.session.generate_reply(
            instructions="Greet the customer as Maria and acknowledge their concern."
        )

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()
    agent_manager = ShopBilisAgentManager()

    agent_manager.session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="coral",
            turn_detection=TurnDetection(
                type="semantic_vad",
                eagerness="high",
                create_response=True,
                interrupt_response=True,
            ),
        )
    )

    await agent_manager.session.start(
        room=ctx.room,
        agent=agent_manager.current_agent
    )

    await agent_manager.session.generate_reply(
        instructions="Greet the user warmly in English, introduce yourself as BILIS, and offer help."
    )

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))