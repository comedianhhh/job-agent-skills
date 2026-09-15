import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // small runtime image for docker-compose
};

export default nextConfig;
