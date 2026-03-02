import { useState, useRef } from 'react';
import { Swiper as SwiperType } from 'swiper';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Story } from '../lib/content';
import LensPane from './LensPane';

// Import Swiper styles
import 'swiper/css';
import './LensSwiper.css';

interface LensSwiperProps {
  story: Story;
}

export default function LensSwiper({ story }: LensSwiperProps) {
  const swiperRef = useRef<SwiperType | null>(null);
  const [activeIndex, setActiveIndex] = useState(1); // Start on neutral (center)

  return (
    <div className="lens-swiper-container">
      <Swiper
        onSwiper={(swiper) => {
          swiperRef.current = swiper;
        }}
        onSlideChange={(swiper) => {
          setActiveIndex(swiper.activeIndex);
        }}
        direction="horizontal"
        slidesPerView={1.06}
        centeredSlides={true}
        spaceBetween={12}
        initialSlide={1} // Start on neutral (center)
        resistance={true}
        resistanceRatio={0.85}
        threshold={10}
        speed={300}
        nested={true} // Allow vertical swiper to work when at edges
        className="lens-swiper"
      >
        <SwiperSlide>
          <LensPane type="left" content={story.left} />
        </SwiperSlide>

        <SwiperSlide>
          <LensPane type="neutral" content={story.neutral} coverImage={story.coverImage} />
        </SwiperSlide>

        <SwiperSlide>
          <LensPane type="right" content={story.right} />
        </SwiperSlide>
      </Swiper>

      {/* Visual indicator for lens position */}
      <div className="lens-indicator">
        <button 
          className={`lens-indicator-pill ${activeIndex === 0 ? 'active' : ''}`}
          onClick={() => swiperRef.current?.slideTo(0)}
          style={{ '--pill-color': 'var(--color-left)' } as React.CSSProperties}
        >
          Left
        </button>
        <button 
          className={`lens-indicator-pill ${activeIndex === 1 ? 'active' : ''}`}
          onClick={() => swiperRef.current?.slideTo(1)}
          style={{ '--pill-color': 'var(--color-centre)' } as React.CSSProperties}
        >
          Centre
        </button>
        <button 
          className={`lens-indicator-pill ${activeIndex === 2 ? 'active' : ''}`}
          onClick={() => swiperRef.current?.slideTo(2)}
          style={{ '--pill-color': 'var(--color-right)' } as React.CSSProperties}
        >
          Right
        </button>
      </div>
    </div>
  );
}
