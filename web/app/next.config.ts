import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // small runtime image for docker-compose; /api/* is proxied by src/app/api/[...path]/route.ts
};

export default nextConfig;
