// index.js
Page({
  data: {
    // 皮皮动图地址
    pipiGifUrl: '/images/pipi.gif'
  },

  onLoad() {
    // 页面加载时检查是否有扫码进入的喂食请求
    const scene = wx.getLaunchOptionsSync().scene;
    const query = wx.getLaunchOptionsSync().query;
    if (query.action === 'feed') {
      wx.redirectTo({
        url: '/pages/scan/scan'
      });
    }

  },

  goToGate() {
    wx.navigateTo({
      url: '/pages/gate/gate'
    });
  },

  goToPet() {
    wx.navigateTo({
      url: '/pages/pet/pet'
    });
  },

  // 隐藏入口：长按标题进入管理中心（仅超级管理员可进入）
  // 长按阈值 2.5 秒，避免误触
  adminTouchTimer: null,
  adminTouchStartTime: 0,

  onAdminTouchStart() {
    this.adminTouchStartTime = Date.now();
    this.adminTouchTimer = setTimeout(() => {
      // 达到长按时间，触发短震动提示
      wx.vibrateShort({ type: 'light' });
      this.enterAdmin();
      this.adminTouchTimer = null;
    }, 2500);
  },

  onAdminTouchEnd() {
    const duration = Date.now() - this.adminTouchStartTime;
    if (this.adminTouchTimer) {
      clearTimeout(this.adminTouchTimer);
      this.adminTouchTimer = null;
    }
    // 如果已经超时触发过 enterAdmin，这里不需要处理
  },

  onAdminTouchMove() {
    // 手指移动时取消长按，防止滑动误触
    if (this.adminTouchTimer) {
      clearTimeout(this.adminTouchTimer);
      this.adminTouchTimer = null;
    }
  },

  enterAdmin() {
    wx.navigateTo({
      url: '/pages/admin/admin'
    });
  }
});
