import './globals.css'

export const metadata = {
  title: 'InfraWatch — Observabilidade & Monitoramento',
  description: 'Plataforma unificada para monitoramento de servidores, containers e métricas',
}

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-[#0b0f19] text-gray-100 flex flex-col antialiased">
        {children}
      </body>
    </html>
  )
}
