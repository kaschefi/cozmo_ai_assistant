import React from 'react';

interface FeatureItem {
  id: string;
  title: string;
  category: string;
  description: string;
  badgeColor: string; // Tailwind color class for border/glow accent
  icon: React.ReactNode;
}

export const FeatureMarquee: React.FC = () => {
  const row1Features: FeatureItem[] = [
    {
      id: 'launcher',
      title: 'Interactive Launcher',
      category: 'System',
      description: 'Unified main.py CLI shell for quick access to Terminal chat mode or physical robot control bridges.',
      badgeColor: 'border-cyan-500 text-cyan-400 shadow-cyan-950/50',
      icon: (
        <svg className="w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      )
    },
    {
      id: 'voice',
      title: 'Voice Wake-Word Input',
      category: 'Interface',
      description: 'Continuous wake-word monitoring ("hey buddy") transcribing live mic input instantly via Google Speech API.',
      badgeColor: 'border-blue-500 text-blue-400 shadow-blue-950/50',
      icon: (
        <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      )
    },
    {
      id: 'tts',
      title: 'Kokoro-ONNX Speech',
      category: 'Cognition',
      description: 'Zero-disk I/O local Text-to-Speech engine producing studio-quality spoken voice in background threads.',
      badgeColor: 'border-purple-500 text-purple-400 shadow-purple-950/50',
      icon: (
        <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        </svg>
      )
    },
    {
      id: 'router1',
      title: 'Layer 1 Router (~50ms)',
      category: 'Latency',
      description: 'Embedding-based instant reflex routing using FastEmbed to bypass local LLMs for core OS operations.',
      badgeColor: 'border-emerald-500 text-emerald-400 shadow-emerald-950/50',
      icon: (
        <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      )
    },
    {
      id: 'rag',
      title: 'FAISS Tool RAG',
      category: 'Intelligence',
      description: 'Dynamically indexes all workflow tools in a local FAISS database, presenting only relevant inputs to the LLM.',
      badgeColor: 'border-[#1c39bb] text-[#6885ff] shadow-[#1c39bb]/50',
      icon: (
        <svg className="w-6 h-6 text-[#6885ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      )
    },
    {
      id: 'mcp',
      title: 'Tavily MCP Client',
      category: 'Search',
      description: 'Leverages the standard Model Context Protocol to run real-time, highly-optimized web searches.',
      badgeColor: 'border-pink-500 text-pink-400 shadow-pink-950/50',
      icon: (
        <svg className="w-6 h-6 text-pink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
        </svg>
      )
    },
    {
      id: 'workstations',
      title: 'Workstation Automation',
      category: 'Control',
      description: 'Custom setups launch application packages and developer sites for Gaming, Study, and Coding routines.',
      badgeColor: 'border-indigo-500 text-indigo-400 shadow-indigo-950/50',
      icon: (
        <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      )
    }
  ];

  const row2Features: FeatureItem[] = [
    {
      id: 'weather',
      title: 'Weather ReAct Agent',
      category: 'Search',
      description: 'Conversational agent that hooks into the wttr.in API to extract local conditions with detailed descriptions.',
      badgeColor: 'border-yellow-500 text-yellow-400 shadow-yellow-950/50',
      icon: (
        <svg className="w-6 h-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
        </svg>
      )
    },
    {
      id: 'calendar',
      title: 'n8n Google Calendar',
      category: 'Integration',
      description: 'Stateful calendar manager connected to Google Calendar via n8n workflows for query/creation loops.',
      badgeColor: 'border-orange-500 text-orange-400 shadow-orange-950/50',
      icon: (
        <svg className="w-6 h-6 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      )
    },
    {
      id: 'docking',
      title: 'OpenCV Auto-Docking',
      category: 'Physical',
      description: 'Guided charger docking using Cozmo camera stream, HSV color filtering, and proportional steering guides.',
      badgeColor: 'border-teal-500 text-teal-400 shadow-teal-950/50',
      icon: (
        <svg className="w-6 h-6 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.475 3.475 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.475 3.475 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.475 3.475 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.475 3.475 0 013.138-3.138z" />
        </svg>
      )
    },
    {
      id: 'face',
      title: 'OLED Face Expressions',
      category: 'Physical',
      description: "Direct drawing of animations, weather graphs, and text widgets onto Cozmo's 128x64 face canvas.",
      badgeColor: 'border-sky-500 text-sky-400 shadow-sky-950/50',
      icon: (
        <svg className="w-6 h-6 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    {
      id: 'timer',
      title: 'Asynchronous Timer',
      category: 'Control',
      description: 'Run background countdowns and timers while pushing live updates to OLED displays and speech nodes.',
      badgeColor: 'border-red-500 text-red-400 shadow-red-950/50',
      icon: (
        <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    {
      id: 'rest',
      title: 'FastAPI REST Bridge',
      category: 'Interface',
      description: 'Exposes all low-level physical capabilities via HTTP endpoints for third-party smart home routines.',
      badgeColor: 'border-lime-500 text-lime-400 shadow-lime-950/50',
      icon: (
        <svg className="w-6 h-6 text-lime-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
      )
    },
    {
      id: 'memory_st',
      title: 'Short-Term Memory',
      category: 'Cognition',
      description: 'Postgres checkpointing (`PostgresSaver`) combined with dynamic context-summarization and trimming nodes.',
      badgeColor: 'border-sky-400 text-sky-300 shadow-sky-950/50',
      icon: (
        <svg className="w-6 h-6 text-sky-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      )
    },
    {
      id: 'memory_lt',
      title: 'Long-Term Memory Core',
      category: 'Cognition',
      description: 'Uses native float arrays, local FastEmbed vectors, and NumPy cosine evaluations for zero-pgvector Windows configurations.',
      badgeColor: 'border-fuchsia-500 text-fuchsia-400 shadow-fuchsia-950/50',
      icon: (
        <svg className="w-6 h-6 text-fuchsia-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      )
    }
  ];

  const renderFeatureCard = (item: FeatureItem) => (
    <div
      key={`${item.id}-card`}
      className="w-80 md:w-96 flex-shrink-0 mx-4 p-6 rounded-2xl bg-[#0e1015]/95 border border-slate-800/80 hover:border-slate-700 hover:shadow-[0_0_30px_rgba(0,243,255,0.12)] transition-all duration-300 group flex flex-col justify-between"
    >
      <div>
        <div className="flex justify-between items-start mb-4">
          <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 group-hover:border-slate-700 group-hover:shadow-[0_0_15px_rgba(0,243,255,0.06)] transition-all duration-300">
            {item.icon}
          </div>
          <span className={`text-[10px] uppercase tracking-widest font-semibold px-2.5 py-0.5 rounded-full border ${item.badgeColor}`}>
            {item.category}
          </span>
        </div>
        <h3 className="text-white text-base font-bold mb-2 tracking-tight group-hover:text-cyan-300 transition-colors duration-300">
          {item.title}
        </h3>
        <p className="text-slate-400 text-xs md:text-sm leading-relaxed">
          {item.description}
        </p>
      </div>
    </div>
  );

  return (
    <div id="features" className="w-full flex flex-col gap-12 relative z-20 scroll-mt-28">
      {/* Centered Heading */}

      <div className="text-center max-w-2xl mx-auto px-4 mb-2 flex flex-col items-center">
        <div className="relative inline-block mb-3">
          <h2 className="font-megrim text-4xl md:text-5xl font-bold text-white tracking-wider leading-tight">
            Agent Capabilities
          </h2>
          <div className="brand-underline" />
        </div>
        <p className="text-slate-400 text-sm md:text-base leading-relaxed">
          Powered by a dual-layer cognitive architecture matching ultra-low latency physical reactions with LangGraph dynamic reasoning pipelines.
        </p>
      </div>

      {/* Marquee Row 1 - Left to Right scrolling */}
      <div className="marquee-container relative w-screen left-[50%] right-[50%] -mx-[50vw] overflow-hidden py-4">
        {/* Soft fading gradients on the sides */}
        <div className="absolute top-0 bottom-0 left-0 w-24 bg-gradient-to-r from-[#08090c] to-transparent z-10 pointer-events-none" />
        <div className="absolute top-0 bottom-0 right-0 w-24 bg-gradient-to-l from-[#08090c] to-transparent z-10 pointer-events-none" />

        <div className="animate-marquee-left will-change-transform">
          {/* First iteration */}
          <div className="flex">
            {row1Features.map((item) => renderFeatureCard(item))}
          </div>
          {/* Second iteration (for seamless infinite effect) */}
          <div className="flex">
            {row1Features.map((item) => renderFeatureCard({ ...item, id: `${item.id}-dup` }))}
          </div>
        </div>
      </div>

      {/* Marquee Row 2 - Right to Left scrolling */}
      <div className="marquee-container relative w-screen left-[50%] right-[50%] -mx-[50vw] overflow-hidden py-4 mb-8">
        {/* Soft fading gradients on the sides */}
        <div className="absolute top-0 bottom-0 left-0 w-24 bg-gradient-to-r from-[#08090c] to-transparent z-10 pointer-events-none" />
        <div className="absolute top-0 bottom-0 right-0 w-24 bg-gradient-to-l from-[#08090c] to-transparent z-10 pointer-events-none" />

        <div className="animate-marquee-right will-change-transform">
          {/* First iteration */}
          <div className="flex">
            {row2Features.map((item) => renderFeatureCard(item))}
          </div>
          {/* Second iteration (for seamless infinite effect) */}
          <div className="flex">
            {row2Features.map((item) => renderFeatureCard({ ...item, id: `${item.id}-dup` }))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FeatureMarquee;
