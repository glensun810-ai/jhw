Component({
  properties: {
    endVal: {
      type: Number,
      value: 0,
      observer: 'start'
    },
    duration: {
      type: Number,
      value: 2 // 秒
    }
  },

  data: {
    displayValue: 0,
    startVal: 0,
    startTime: null,
    frameId: null
  },

  methods: {
    start() {
      if (this.data.frameId) {
        cancelAnimationFrame(this.data.frameId);
      }
      this.setData({
        startVal: this.data.displayValue, // 从当前显示值开始
        startTime: null,
      });
      this.data.frameId = requestAnimationFrame(this.count.bind(this));
    },

    count(timestamp) {
      if (!this.data.startTime) {
        this.setData({ startTime: timestamp });
      }

      const progress = timestamp - this.data.startTime;
      const duration = this.properties.duration * 1000;
      
      if (progress < duration) {
        const percentage = progress / duration;
        const nextValue = this.data.startVal + (this.properties.endVal - this.data.startVal) * percentage;
        this.setData({
          displayValue: Math.round(nextValue)
        });
        this.data.frameId = requestAnimationFrame(this.count.bind(this));
      } else {
        this.setData({
          displayValue: this.properties.endVal
        });
      }
    }
  }
});