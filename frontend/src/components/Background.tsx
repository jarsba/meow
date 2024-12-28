interface BackgroundProps {
  children: React.ReactNode;
}

const Background = ({ children }: BackgroundProps) => {
  const lightPattern = `data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23dfd9e9' fill-opacity='0.4' fill-rule='evenodd'%3E%3Ccircle cx='3' cy='3' r='3'/%3E%3Ccircle cx='13' cy='13' r='3'/%3E%3C/g%3E%3C/svg%3E`;
  
  const darkPattern = `data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23312e81' fill-opacity='0.4' fill-rule='evenodd'%3E%3Ccircle cx='3' cy='3' r='3'/%3E%3Ccircle cx='13' cy='13' r='3'/%3E%3C/g%3E%3C/svg%3E`;

  return (
    <div 
      className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-200"
      style={{
        backgroundImage: `url("${lightPattern}")`,
        backgroundAttachment: 'fixed',
        backgroundRepeat: 'repeat',
        backgroundSize: '20px 20px',
      }}
    >
      <style>
        {`
          :root { --pattern: url("${lightPattern}"); }
          :root[class~="dark"] { --pattern: url("${darkPattern}"); }
        `}
      </style>
      <div className="min-h-screen bg-gradient-to-br from-white/10 dark:from-black/10 to-transparent">
        {children}
      </div>
    </div>
  );
};

export default Background; 