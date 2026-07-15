import Link from 'next/link';
export default function NotFound() { return <div className="min-h-[60vh] flex items-center justify-center p-4"><div className="text-center"><h1 className="text-3xl font-bold mb-2">404</h1><p className="text-surface-500 mb-6">Page not found.</p><Link href="/dashboard" className="btn btn-primary">Dashboard</Link></div></div>; }
