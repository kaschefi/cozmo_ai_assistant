import React from 'react';
import { MokaLanding } from './features/landing';
import { ChatInterface, clearTabActiveSession } from './features/chat';
import { CozmoDashboard } from './features/cozmo';
import { BachelorThesisPage } from './features/bachelor-thesis';
import { useLocation } from './shared/hooks';

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

  if (path === '/bachelor-thesis' || path === '/bachelor-thesis/' || path === '/thesis' || path === '/thesis/') {
    return (
      <BachelorThesisPage
        onBackToLanding={() => {
          clearTabActiveSession();
          navigate('/');
        }}
        onStartChat={() => {
          clearTabActiveSession();
          navigate('/chat');
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


