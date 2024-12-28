import React from 'react';
import logo from '../../assets/logo.png';

interface LogoProps {
  isLoading?: boolean;
}

const Logo = ({ isLoading = false }: LogoProps) => {
  return (
    <div className="flex items-center justify-center mb-8">
      <img 
        src={logo} 
        alt="Meow Video Stitcher" 
        className={`
          h-24 w-auto transition-all 
          hover:scale-105
          ${isLoading ? 'animate-spin-slow' : ''}
        `}
      />
    </div>
  );
};

export default Logo; 