import "./globals.css";

export const metadata = { title: "ORBIT · Market Intelligence", description: "Read-only market and portfolio intelligence" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
