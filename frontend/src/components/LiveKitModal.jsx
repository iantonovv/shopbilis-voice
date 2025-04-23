// LiveKitModal.jsx
import { useState, useEffect, useCallback } from "react";
import { LiveKitRoom, RoomAudioRenderer, useConnectionState } from "@livekit/components-react";
import "@livekit/components-styles";
import SimpleVoiceAssistant from "./SimpleVoiceAssistant";

const LiveKitModal = ({ setShowSupport }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [showModal, setShowModal] = useState(true);

  // Function to generate a random 6-letter string
  const generateRandomName = () => {
    const characters = 'abcdefghijklmnopqrstuvwxyz';
    let result = '';
    for (let i = 0; i < 6; i++) {
      result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
  };

  const getToken = useCallback(async (userName) => {
    try {
      console.log("Getting token for user:", userName);
      const response = await fetch(
        `/api/getToken?name=${encodeURIComponent(userName)}`
      );
      const token = await response.text();
      setToken(token);
      setIsLoading(false);
    } catch (error) {
      console.error("Error getting token:", error);
      setIsLoading(false);
    }
  }, []);

  // Automatically generate name and get token on component mount
  useEffect(() => {
    const randomName = generateRandomName();
    getToken(randomName);
  }, [getToken]);

  // When connected, hide the modal but keep the voice assistant
  const handleConnected = () => {
    setIsConnected(true);
    setShowModal(false);
  };

  const handleCloseClick = () => {
    // If we're still connecting, fully close everything
    if (!isConnected) {
      setShowSupport(false);
    } else {
      // If already connected, just hide the modal
      setShowModal(false);
    }
  };

  return (
    <>
      {/* Modal overlay and content */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="support-room">
              {isLoading ? (
                <div className="loading">Connecting to support...</div>
              ) : token ? (
                <div className="loading">Connecting to support...</div>
              ) : (
                <div className="loading">Failed to connect. Please try again.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* LiveKit room container - always present once token is available */}
      {token && (
        <LiveKitRoom
          serverUrl={import.meta.env.VITE_LIVEKIT_URL}
          token={token}
          connect={true}
          video={false}
          audio={true}
          onDisconnected={() => {
            setShowSupport(false);
          }}
        >
          <ConnectionMonitor onConnected={handleConnected} />
          <RoomAudioRenderer />
          
          {/* Voice assistant container - positioned outside the modal */}
          <div className={`voice-assistant-wrapper ${isConnected ? 'visible' : 'hidden'}`}>
            <SimpleVoiceAssistant />
          </div>
        </LiveKitRoom>
      )}
    </>
  );
};

// Connection monitor component
const ConnectionMonitor = ({ onConnected }) => {
  const connectionState = useConnectionState();
  const [hasTriggered, setHasTriggered] = useState(false);
  
  useEffect(() => {
    if (connectionState === "connected" && !hasTriggered) {
      setHasTriggered(true);
      
      // Wait a moment to ensure everything is loaded
      setTimeout(() => {
        if (typeof onConnected === 'function') {
          onConnected();
        }
      }, 1000);
    }
  }, [connectionState, hasTriggered, onConnected]);
  
  return null;
};

export default LiveKitModal;