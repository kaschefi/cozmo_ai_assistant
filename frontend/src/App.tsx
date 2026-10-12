import React from 'react';
import MokaLanding from './components/MokaLanding';
import ChatInterface from './components/ChatInterface';
import CozmoDashboard from './components/CozmoDashboard';
import { useLocation } from './hooks/useLocation';
import { clearTabActiveSession } from './lib/chatHistory';

/**
 * Main App component.
 * Manages routing dynamically based on URL pathnames.
 */
export const App: React.FC = () => {
  const [path, navigate] = useLocation();

  if (path === '/cozmo' || path === '/cozmo/') {
    return (
      <CozmoDashboard
        onBackToChat={() => navigate('/chat')}
        onBackToLanding={() => {
          clearTabActiveSession();
          navigate('/');
        }}
      />
    );
  }

  return path === '/chat' || path === '/chat/' ? (
    <ChatInterface
      onBackToLanding={() => {
        clearTabActiveSession();
        navigate('/');
      }}
    />
  ) : (
    <MokaLanding 
      onStartChat={() => {
        clearTabActiveSession();
        navigate('/chat');
      }} 
      onNavigateToCozmo={() => navigate('/cozmo')}
    />
  );
};

export default App;


