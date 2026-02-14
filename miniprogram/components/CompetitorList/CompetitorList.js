// components/CompetitorList/CompetitorList.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    competitionData: {
      type: Object,
      value: null
    },
    title: {
      type: String,
      value: '品牌认知占位分析'
    },
    loading: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    brandKeywords: [],
    sharedKeywords: []
  },

  /**
   * 组件的方法列表
   */
  methods: {
    updateKeywordData() {
      if (!this.properties.competitionData) {
        this.setData({
          brandKeywords: [],
          sharedKeywords: []
        });
        return;
      }

      // 从 competitionData 中提取关键词数据
      const competitionData = this.properties.competitionData;
      
      // 提取本品牌核心词
      const brandKeywords = Array.isArray(competitionData.brand_keywords) 
        ? competitionData.brand_keywords 
        : Array.isArray(competitionData.brandKeywords) 
          ? competitionData.brandKeywords 
          : [];
          
      // 提取竞品重叠词
      const sharedKeywords = Array.isArray(competitionData.shared_keywords) 
        ? competitionData.shared_keywords 
        : Array.isArray(competitionData.sharedKeywords) 
          ? competitionData.sharedKeywords 
          : [];

      this.setData({
        brandKeywords: brandKeywords,
        sharedKeywords: sharedKeywords
      });
    }
  },
  
  lifetimes: {
    attached() {
      // 组件实例进入页面节点树时执行
    },
    ready() {
      // 组件在视图层布局完成后执行
      this.updateKeywordData();
    },
    detached() {
      // 组件实例被从页面节点树移除时执行
    }
  },
  
  observers: {
    'competitionData': function(newCompetitionData) {
      if (newCompetitionData) {
        this.updateKeywordData();
      }
    }
  }
})