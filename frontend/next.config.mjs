/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  reactStrictMode: true,
  // Permite que el frontend renderice las imágenes generadas
  // (blob storage de Azure). Reemplazar el hostname con el de tu storage.
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.blob.core.windows.net",
      },
    ],
    unoptimized: true,
  },
};

export default nextConfig;
