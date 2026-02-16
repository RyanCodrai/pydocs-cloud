"use client";

import { useState } from "react";
import Image from "next/image";
import { Copy, Check, Github } from "lucide-react";

const INSTALL_COMMAND = "curl -sL sourced.dev/install | sh";

export default function Home() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(INSTALL_COMMAND);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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

          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-stone-800">
            sourced.dev
          </h1>

          <p className="text-stone-500 text-base sm:text-lg leading-relaxed">
            Give your coding agent access to dependency source code.
          </p>

          {/* Install section */}
          <div className="w-full mt-8">
            <h2 className="text-xl sm:text-2xl font-semibold text-stone-800 mb-4">
              Setup MCP
            </h2>
            <div className="flex items-center rounded-lg border border-stone-200 bg-white shadow-sm overflow-hidden">
              <span className="select-none pl-4 pr-2 text-stone-400">$</span>
              <code className="flex-1 py-3 text-sm sm:text-base text-amber-700 select-all">
                {INSTALL_COMMAND}
              </code>
              <button
                onClick={handleCopy}
                className="px-4 py-3 text-stone-400 hover:text-stone-700 transition-colors"
                aria-label="Copy to clipboard"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* GitHub link */}
          <a
            href="https://github.com/RyanCodrai/sourced"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-stone-500 hover:text-amber-700 transition-colors"
          >
            <Github className="h-4 w-4" />
            Open source on GitHub
          </a>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-8 text-center mt-auto">
        <p className="text-sm text-stone-500">
          Built with ❤️ by{" "}
          <a
            href="https://www.linkedin.com/in/ryan-codrai/"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-amber-700"
          >
            Ryan
          </a>{" "}
          in London
        </p>
      </footer>
    </div>
  );
}
