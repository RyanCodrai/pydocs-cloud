import Image from "next/image";

export default function Authenticated() {
  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-stone-50 via-amber-50/30 to-orange-50/20">
      <main className="flex-1 flex flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center gap-8 max-w-2xl text-center">
          <Image
            src="/logo.png"
            alt="sourced.dev"
            width={140}
            height={140}
            priority
          />

          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-stone-800 whitespace-nowrap">
            You have successfully authenticated
          </h1>

          <p className="text-stone-500 text-base sm:text-lg leading-relaxed">
            You can now close this tab and return to your terminal
          </p>
        </div>
      </main>
    </div>
  );
}
