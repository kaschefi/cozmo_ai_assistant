import React from 'react';

interface ChatBoxProps {
  isChatActive: boolean;
}

/**
 * ChatBox component rendering the interactive dialogue layout.
 * Leverages React.forwardRef to expose its outer container to viewport boundary tracking.
 */
export const ChatBox = React.forwardRef<HTMLDivElement, ChatBoxProps>(
  ({ isChatActive }, ref) => {
    return (
      <div 
        ref={ref}
        className={`w-full max-w-[800px] mx-auto rounded-[24px] bg-[#020512]/40 backdrop-blur-md flex flex-col justify-between overflow-hidden transition-all duration-700 ease-in-out relative ${
          isChatActive 
            ? 'opacity-100 translate-y-0 scale-100' 
            : 'opacity-0 translate-y-8 scale-95 pointer-events-none'
        }`}
        style={{
          height: '450px',
        }}
      >
        {/* Empty chat body - no default messages */}
        <div className="flex-1 overflow-y-auto p-6" />

        {/* Text input area at the bottom to talk to Moka */}
        <div className="h-16 border-t border-slate-900/10 bg-slate-950/20 px-6 flex items-center">
          <input 
            type="text" 
            placeholder="Send a message to Moka..." 
            className="w-full bg-transparent border-none outline-none text-white font-medium placeholder-slate-500 font-sans text-sm"
          />
          <button className="text-cyan-400 font-semibold text-sm tracking-wider hover:text-cyan-300 transition-colors uppercase ml-4 cursor-pointer">
            Send
          </button>
        </div>
      </div>
    );
  }
);

ChatBox.displayName = 'ChatBox';

export default ChatBox;
