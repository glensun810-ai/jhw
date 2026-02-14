// components/Skeleton/Skeleton.js
Component({
  options: {
    addGlobalClass: true
  },

  /**
   * 组件的属性列表
   */
  properties: {
    // 是否显示骨架屏
    loading: {
      type: Boolean,
      value: true
    },
    // 骨架屏类型：text, rect, circle, paragraph
    type: {
      type: String,
      value: 'rect'
    },
    // 骨架屏行数（当type为paragraph时有效）
    rows: {
      type: Number,
      value: 3
    },
    // 骨架屏宽度
    width: {
      type: String,
      value: '100%'
    },
    // 骨架屏高度
    height: {
      type: String,
      value: '20px'
    },
    // 是否显示动画
    animated: {
      type: Boolean,
      value: true
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    rowList: []
  },

  /**
   * 组件的方法列表
   */
  methods: {},

  lifetimes: {
    attached: function() {
      if (this.properties.type === 'paragraph') {
        const rowList = [];
        for (let i = 0; i < (this.properties.rows || 3); i++) {
          rowList.push(i);
        }
        this.setData({ rowList });
      } else {
        this.setData({ rowList: [0] });
      }
    }
  }
})