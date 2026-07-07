import React, { useRef, useState } from 'react';
import Header from './ui/Header';
import WelcomeCard from './ui/WelcomeCard';
import FeatureGrid from './ui/FeatureGrid';
import ChatBox from './ui/ChatBox';
import ParticleCanvas from './ui/ParticleCanvas';

/**
 * MokaLanding component representing the main ecosystem dashboard.
 * Abstracted into modular sub-components for enhanced readability, separation of concerns,
 * and component-driven architecture.
 */
export const MokaLanding: React.FC = () => {
  const chatBoxRef = useRef<HTMLDivElement | null>(null);
  const [isChatActive, setIsChatActive] = useState(false);

  return (
    <div className="relative min-h-[220vh] bg-gradient-to-br from-[#020512] via-[#070b1a] to-[#020512] overflow-x-hidden select-none">
      {/* Subtle digital grid overlay */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-[0.03] z-10"
        style={{
          backgroundImage: 'radial-gradient(circle, #00f3ff 1px, transparent 1px)',
          backgroundSize: '30px 30px'
        }}
      />
      
      {/* Fixed Sticky Header Bar */}
      <Header />
      
      {/* Fixed canvas on top of everything so particles float over the header and content */}
      <ParticleCanvas 
        chatBoxRef={chatBoxRef} 
        onChatActiveChange={setIsChatActive} 
      />

      {/* Fixed dark vignette overlay to keep contrast high */}
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_center,transparent_20%,rgba(2,5,18,0.85)_100%)] pointer-events-none z-16" />

      {/* Foreground content card that scrolls up */}
      <div className="relative w-full max-w-5xl mx-auto px-6 pt-[105vh] pb-32 z-20 pointer-events-auto">
        {/* Welcome card introducing the ecosystem */}
        <WelcomeCard />

        {/* Feature Grid representing three core services */}
        <FeatureGrid />

        {/* Dynamic Flow Chat Box container */}
        <ChatBox 
          ref={chatBoxRef} 
          isChatActive={isChatActive} 
        />
      </div>
    </div>
  );
};

export default MokaLanding;
