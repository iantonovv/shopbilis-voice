// src/App.jsx
import React, { useState } from 'react';
import './App.css';
import LiveKitModal from './components/LiveKitModal';

function App() {
  const [showSupport, setShowSupport] = useState(false);

  const handleSupportClick = () => {
    setShowSupport(true);
  };

  return (
    <div className="app">
      <main>
        <button className="support-button" onClick={handleSupportClick}>
        <img src="src/assets/mic.png" width="40"/>
        </button>
      </main>

      {showSupport && <LiveKitModal setShowSupport={setShowSupport} />}
    </div>
  );
}

// Function to initialize and render the app in the given container
export const initChatApp = (container) => {
  const root = ReactDOM.createRoot(container);
  root.render(<App />);
};

export default App;
