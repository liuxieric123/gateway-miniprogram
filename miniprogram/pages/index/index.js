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
  }
});
