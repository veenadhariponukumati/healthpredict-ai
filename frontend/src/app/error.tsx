'use client';
export default function Error({ error, reset }: { error: Error; reset: () => void }) { return <div className="min-h-[60vh] flex items-center justify-center p-4"><div className="text-center"><h1 className="text-3xl font-bold mb-2">500</h1><p className="text-surface-500 mb-4">Something went wrong.</p><button onClick={reset} className="btn btn-primary">Try again</button></div></div>; }
