import React from 'react';
import MokaLanding from './components/MokaLanding';
import ChatInterface from './components/ChatInterface';
import CozmoDashboard from './components/CozmoDashboard';
import { useLocation } from './hooks/useLocation';

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
        onBackToLanding={() => navigate('/')}
      />
    );
  }

  return path === '/chat' || path === '/chat/' ? (
    <ChatInterface onBackToLanding={() => navigate('/')} />
  ) : (
    <MokaLanding onStartChat={() => navigate('/chat')} />
  );
};

export default App;


