import { useEffect, useRef } from 'react';
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

  return (
    <div className="lens-swiper-container">
      <Swiper
        onSwiper={(swiper) => {
          swiperRef.current = swiper;
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
        <div className="lens-indicator-dot" data-active={swiperRef.current?.activeIndex === 0} style={{ background: 'var(--color-left)' }} />
        <div className="lens-indicator-dot" data-active={swiperRef.current?.activeIndex === 1} style={{ background: 'var(--color-centre)' }} />
        <div className="lens-indicator-dot" data-active={swiperRef.current?.activeIndex === 2} style={{ background: 'var(--color-right)' }} />
      </div>
    </div>
  );
}
