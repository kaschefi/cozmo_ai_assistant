import React from 'react';

/**
 * FeatureGrid component rendering the core capabilities of the Moka platform in a 3-column grid.
 */
export const FeatureGrid: React.FC = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-24">
      <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-md">
        <div className="text-cyan-400 text-3xl font-bold mb-4">01</div>
        <h3 className="text-lg font-bold text-white mb-2">Autonomous Pipelines</h3>
        <p className="text-slate-400 text-sm leading-relaxed">
          Configure self-healing workflows that run scripts, verify outputs, and execute corrections locally.
        </p>
      </div>
      <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-md">
        <div className="text-cyan-400 text-3xl font-bold mb-4">02</div>
        <h3 className="text-lg font-bold text-white mb-2">Speech Synthesizer</h3>
        <p className="text-slate-400 text-sm leading-relaxed">
          High-fidelity TTS utilizing Kokoro ONNX to give your local agent voice interfaces that feel organic.
        </p>
      </div>
      <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-md">
        <div className="text-cyan-400 text-3xl font-bold mb-4">03</div>
        <h3 className="text-lg font-bold text-white mb-2">Secure Verification</h3>
        <p className="text-slate-400 text-sm leading-relaxed">
          Keeps humans in the loop with cryptographic verification before committing write operations.
        </p>
      </div>
    </div>
  );
};

export default FeatureGrid;
