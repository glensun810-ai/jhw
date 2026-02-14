Page({
  data: {
    id: '',
    brandName: '',
    tags: [],
    categories: ['未分类', '日常监测', '竞品分析', '季度报告', '年度总结'],
    selectedCategory: '未分类',
    categoryIndex: 0,
    notes: '',
    isFavorite: false,
    newTag: ''
  },

  onLoad: function(options) {
    const id = options.id;
    this.setData({
      id: id
    });
    
    this.loadResult(id);
  },

  loadResult: function(id) {
    try {
      const savedResults = wx.getStorageSync('savedSearchResults') || [];
      const result = savedResults.find(item => item.id === id);
      
      if (result) {
        this.setData({
          brandName: result.brandName,
          tags: result.tags || [],
          selectedCategory: result.category || '未分类',
          categoryIndex: this.data.categories.indexOf(result.category || '未分类'),
          notes: result.notes || '',
          isFavorite: result.isFavorite || false
        });
      }
    } catch (e) {
      console.error('加载保存的搜索结果失败', e);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  onBrandNameInput: function(e) {
    this.setData({
      brandName: e.detail.value
    });
  },

  onNewTagInput: function(e) {
    this.setData({
      newTag: e.detail.value
    });
  },

  addTag: function() {
    if (this.data.newTag.trim() && !this.data.tags.includes(this.data.newTag.trim())) {
      const tags = [...this.data.tags, this.data.newTag.trim()];
      this.setData({
        tags: tags,
        newTag: ''
      });
    }
  },

  removeTag: function(e) {
    const index = e.currentTarget.dataset.index;
    const tags = [...this.data.tags];
    tags.splice(index, 1);
    this.setData({
      tags: tags
    });
  },

  onCategoryChange: function(e) {
    const index = e.detail.value;
    const category = this.data.categories[index];
    this.setData({
      categoryIndex: index,
      selectedCategory: category
    });
  },

  onNotesInput: function(e) {
    this.setData({
      notes: e.detail.value
    });
  },

  onFavoriteChange: function(e) {
    this.setData({
      isFavorite: e.detail.value
    });
  },

  saveChanges: function() {
    if (!this.data.brandName.trim()) {
      wx.showToast({
        title: '请输入品牌名称',
        icon: 'none'
      });
      return;
    }

    try {
      const savedResults = wx.getStorageSync('savedSearchResults') || [];
      const index = savedResults.findIndex(item => item.id === this.data.id);
      
      if (index !== -1) {
        savedResults[index] = {
          ...savedResults[index],
          brandName: this.data.brandName.trim(),
          tags: this.data.tags,
          category: this.data.selectedCategory,
          notes: this.data.notes,
          isFavorite: this.data.isFavorite
        };
        
        wx.setStorageSync('savedSearchResults', savedResults);
        
        wx.showToast({
          title: '保存成功',
          icon: 'success'
        });
        
        // 返回上一页
        wx.navigateBack();
      } else {
        wx.showToast({
          title: '找不到对应记录',
          icon: 'none'
        });
      }
    } catch (e) {
      console.error('保存更改失败', e);
      wx.showToast({
        title: '保存失败',
        icon: 'none'
      });
    }
  },

  cancelEdit: function() {
    wx.navigateBack();
  }
})