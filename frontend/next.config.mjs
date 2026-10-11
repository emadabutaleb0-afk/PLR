/** @type {import('next').NextConfig} */
const backend = process.env.BACKEND_URL || "http://localhost:8000";
export default {
  // Docker image sets NEXT_STANDALONE=1; local `npm start` / `npm run dev` work normally without it
  ...(process.env.NEXT_STANDALONE ? { output: "standalone" } : {}),
  poweredByHeader: false,
  async rewrites() { return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }]; },
  async headers() {
    return [{ source: "/(.*)", headers: [
      { key: "X-Frame-Options", value: "DENY" }, { key: "X-Content-Type-Options", value: "nosniff" }, { key: "Referrer-Policy", value: "no-referrer" },
    ] }];
  },
};
