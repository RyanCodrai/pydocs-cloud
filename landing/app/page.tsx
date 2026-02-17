"use client";

import { useState } from "react";
import Image from "next/image";
import { Copy, Check, Github, ChevronDown, Code, Zap, Package } from "lucide-react";

const INSTALL_COMMAND = "curl -sL sourced.dev/install | sh";

export default function Home() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(INSTALL_COMMAND);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gradient-to-br from-stone-50 via-amber-50/30 to-orange-50/20">
      {/* Hero — fills exactly one viewport */}
      <section className="h-screen flex flex-col px-6">
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="flex flex-col items-center gap-6 max-w-2xl text-center">
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
              Give your coding agent access to dependency source code
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
        </div>

        {/* Footer pinned at bottom of hero viewport */}
        <footer className="py-6 text-center flex flex-col items-center gap-4">
          <ChevronDown className="h-5 w-5 text-stone-300 animate-bounce" />
          <p className="text-sm text-stone-500">
            Built with &#10084;&#65039; by{" "}
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
      </section>

      <div className="h-16 sm:h-20" />

      {/* Grid */}
      <section className="border-y border-stone-200/60">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 sm:grid-cols-[auto_1fr_1fr_1fr]">
            <div className="py-20 sm:py-24 sm:pr-8 flex items-start">
              <h2 className="text-xl sm:text-2xl font-semibold text-stone-800">
                Why sourced.dev
              </h2>
            </div>

            <div className="border-t sm:border-t-0 sm:border-l border-stone-200/60 py-20 sm:py-24 sm:px-8">
              <div className="flex items-center gap-3 mb-20">
                <Code className="h-6 w-6 text-stone-800" />
                <h2 className="text-xl sm:text-2xl font-semibold text-stone-800">
                  Source of truth
                </h2>
              </div>
              <p className="text-base text-stone-900 leading-relaxed">
                Allow your agent to explore dependency source code as if it
                were on your local machine. Resolved directly from package
                metadata.
              </p>
            </div>

            <div className="border-t sm:border-t-0 sm:border-l border-stone-200/60 py-20 sm:py-24 sm:px-8">
              <div className="flex items-center gap-3 mb-20">
                <Package className="h-6 w-6 text-stone-800" />
                <h2 className="text-xl sm:text-2xl font-semibold text-stone-800">
                  Every package
                </h2>
              </div>
              <p className="text-base text-stone-900 leading-relaxed">
                Not just the popular ones — all packages are continually
                indexed in real time. 700k+ Python and 3.5m+ NPM packages.
              </p>
            </div>

            <div className="border-t sm:border-t-0 sm:border-l border-stone-200/60 py-20 sm:py-24 sm:pl-8">
              <div className="flex items-center gap-3 mb-20">
                <Zap className="h-6 w-6 text-stone-800" />
                <h2 className="text-xl sm:text-2xl font-semibold text-stone-800">
                  Version-pinned
                </h2>
              </div>
              <p className="text-base text-stone-900 leading-relaxed">
                Each release is mapped to its source code at the time it was
                published. Your agent reads the code that exists for the
                version your project depends on.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="px-6 py-32 sm:py-40 border-t border-stone-200/60">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-stone-800 mb-4">
            Get started
          </h2>
          <p className="text-stone-500 text-base sm:text-lg mb-8">
            Set up in seconds. Works across Claude, Codex, and more.
          </p>
          <div className="flex items-center rounded-lg border border-stone-200 bg-white shadow-sm overflow-hidden max-w-lg mx-auto">
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

          <a
            href="https://github.com/RyanCodrai/sourced"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-stone-500 hover:text-amber-700 transition-colors mt-6"
          >
            <Github className="h-4 w-4" />
            Open source on GitHub
          </a>
        </div>
      </section>

    </div>
  );
}
