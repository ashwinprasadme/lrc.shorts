import { useEffect, useRef } from 'react';
import { Swiper as SwiperType } from 'swiper';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Keyboard, Mousewheel } from 'swiper/modules';
import type { Story } from '../lib/content';
import StoryCard from './StoryCard';

// Import Swiper styles
import 'swiper/css';
import './ReelFeed.css';

interface ReelFeedProps {
  stories: Story[];
  initialSlide?: number;
}

export default function ReelFeed({ stories, initialSlide = 0 }: ReelFeedProps) {
  const swiperRef = useRef<SwiperType | null>(null);

  useEffect(() => {
    const handleLensChange = (mutations: MutationRecord[]) => {
      if (swiperRef.current) {
        const activeSlide = swiperRef.current.slides[swiperRef.current.activeIndex];
        const activeLens = activeSlide?.querySelector('[data-active-lens]')?.getAttribute('data-active-lens');
        
        // Disable vertical scrolling when on left or right lens
        const shouldDisable = activeLens === 'left' || activeLens === 'right';
        
        if (shouldDisable) {
          swiperRef.current.disable();
        } else {
          swiperRef.current.enable();
        }
      }
    };

    // Create a single observer for all lens changes
    const observer = new MutationObserver(handleLensChange);
    
    // Function to observe all current lens containers
    const observeAllLensContainers = () => {
      const lensContainers = document.querySelectorAll('[data-active-lens]');
      lensContainers.forEach(container => {
        observer.observe(container, {
          attributes: true,
          attributeFilter: ['data-active-lens']
        });
      });
    };

    // Initial observation
    observeAllLensContainers();

    // Re-observe when swiper updates (for lazy-loaded slides)
    const reobserveInterval = setInterval(observeAllLensContainers, 1000);

    return () => {
      observer.disconnect();
      clearInterval(reobserveInterval);
    };
  }, []);

  useEffect(() => {
    // Optional: Update URL when slide changes
    if (swiperRef.current) {
      swiperRef.current.on('slideChange', (swiper) => {
        const currentStory = stories[swiper.activeIndex];
        if (currentStory && window.history) {
          window.history.replaceState(
            null,
            '',
            `/story/${currentStory.slug}/`
          );
        }
      });
    }

    return () => {
      if (swiperRef.current) {
        swiperRef.current.off('slideChange');
      }
    };
  }, [stories]);

  return (
    <div className="reel-feed">
      <Swiper
        onSwiper={(swiper) => {
          swiperRef.current = swiper;
        }}
        modules={[Keyboard, Mousewheel]}
        direction="vertical"
        slidesPerView={1}
        initialSlide={initialSlide}
        resistance={true}
        resistanceRatio={0.85}
        threshold={10}
        speed={400}
        keyboard={{
          enabled: true,
          onlyInViewport: true,
        }}
        mousewheel={{
          forceToAxis: true,
          sensitivity: 1,
          releaseOnEdges: false,
        }}
        className="reel-swiper"
      >
        {stories.map((story) => (
          <SwiperSlide key={story.slug}>
            <StoryCard story={story} />
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}
