// Loading indicator: a gold dot orbiting a faint ring.
export function Loader({ label, className = "" }: { label?: string; className?: string }) {
  return (
    <div role="status" aria-live="polite" className={`flex flex-col items-center justify-center gap-4 py-20 ${className}`}>
      <span className="relative block h-12 w-12">
        <span className="absolute inset-0 rounded-full border-2 border-amber-500/20" />
        <span className="absolute inset-0 animate-spin [animation-duration:1.1s]">
          <span className="absolute left-1/2 top-0 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-400 shadow-[0_0_14px_rgba(245,184,61,0.85)]" />
        </span>
        <span className="absolute inset-[30%] rounded-full bg-amber-500/10" />
      </span>
      {label && <p className="text-sm opacity-70">{label}</p>}
    </div>
  );
}