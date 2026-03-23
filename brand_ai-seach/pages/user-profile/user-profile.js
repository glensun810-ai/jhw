const { getUserProfile, updateUserProfile } = require('../../api/user');
const { logout: authLogout } = require('../../utils/auth');

Page({
  data: {
    userId: '',
    phone: '',
    nickname: '',
    avatarUrl: '',
    createdAt: '',
    saving: false,
    hasChanges: false
  },

  onLoad: function(options) {
    console.log('User profile page loaded');
    this.loadUserProfile();
  },

  /**
   * 加载用户资料
   */
  async loadUserProfile() {
    try {
      wx.showLoading({ title: '加载中...' });
      
      const res = await getUserProfile();
      
      if (res && res.status === 'success' && res.profile) {
        const profile = res.profile;
        
        this.setData({
          userId: profile.user_id,
          phone: profile.phone,
          nickname: profile.nickname || '',
          avatarUrl: profile.avatar_url || '',
          createdAt: profile.created_at ? this.formatDate(profile.created_at) : ''
        });
      }
      
      wx.hideLoading();
    } catch (error) {
      console.error('Failed to load user profile:', error);
      wx.hideLoading();
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  /**
   * 昵称输入
   */
  onNicknameInput: function(e) {
    const value = e.detail.value;
    this.setData({
      nickname: value,
      hasChanges: true
    });
  },

  /**
   * 选择头像
   */
  chooseAvatar: function() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0];
        console.log('Selected avatar:', tempFilePath);
        
        // 这里可以添加上传头像到服务器的逻辑
        // 目前只更新本地显示
        this.setData({
          avatarUrl: tempFilePath,
          hasChanges: true
        });
        
        wx.showToast({
          title: '头像已选择',
          icon: 'success'
        });
      },
      fail: (err) => {
        console.error('Failed to choose image:', err);
      }
    });
  },

  /**
   * 保存资料
   */
  async saveProfile() {
    if (!this.data.hasChanges) {
      wx.showToast({
        title: '暂无修改',
        icon: 'none'
      });
      return;
    }

    if (!this.data.nickname || this.data.nickname.trim() === '') {
      wx.showToast({
        title: '昵称不能为空',
        icon: 'none'
      });
      return;
    }

    try {
      this.setData({ saving: true });
      
      // 准备更新数据
      const updateData = {
        nickname: this.data.nickname.trim()
      };
      
      // 如果有头像上传，添加头像 URL
      if (this.data.avatarUrl && this.data.avatarUrl.startsWith('http')) {
        updateData.avatar_url = this.data.avatarUrl;
      }
      
      const res = await updateUserProfile(updateData);
      
      this.setData({ saving: false });
      
      if (res && res.status === 'success') {
        wx.showToast({
          title: '保存成功',
          icon: 'success'
        });
        
        this.setData({ hasChanges: false });
        
        // 更新本地缓存的用户信息
        const userInfo = wx.getStorageSync('userInfo');
        if (userInfo) {
          userInfo.nickname = this.data.nickname;
          wx.setStorageSync('userInfo', userInfo);
        }
      } else {
        wx.showToast({
          title: res?.error || '保存失败',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('Failed to save profile:', error);
      this.setData({ saving: false });
      wx.showToast({
        title: error?.message || '网络错误',
        icon: 'none'
      });
    }
  },

  /**
   * 退出登录
   */
  logout: function() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          // 清除本地存储
          authLogout();
          
          wx.showToast({
            title: '已退出登录',
            icon: 'success'
          });
          
          // 跳转到登录页
          setTimeout(() => {
            wx.reLaunch({
              url: '/pages/login/login'
            });
          }, 1000);
        }
      }
    });
  },

  /**
   * 格式化日期
   */
  formatDate: function(dateString) {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    } catch (e) {
      return dateString;
    }
  }
});
