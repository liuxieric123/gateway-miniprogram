// pages/pet/pet.js
Page({
  data: {
    // 宠物信息
    petInfo: {
      name: '旺财',
      type: '金毛犬',
      age: '3岁',
      avatar: '🐕'
    },
    // 喂食记录
    feedRecords: [],
    // 今日喂食次数
    todayCount: 0,
    // 二维码页面路径（固定值）
    qrPagePath: 'pages/scan/scan?action=feed',
    // 是否显示二维码弹窗
    showQrModal: false
  },

  onLoad() {
    this.loadFeedRecords();
  },

  onShow() {
    this.loadFeedRecords();
  },

  // 加载喂食记录
  loadFeedRecords() {
    const records = wx.getStorageSync('feed_records') || [];
    const today = new Date().toDateString();
    const todayCount = records.filter(r => new Date(r.time).toDateString() === today).length;

    this.setData({
      feedRecords: records.slice(0, 30),
      todayCount
    });
  },

  // 手动喂食
  manualFeed() {
    wx.showModal({
      title: '确认喂食',
      content: '确认记录一次手动喂食吗？',
      confirmColor: '#4CAF50',
      success: (res) => {
        if (res.confirm) {
          this.recordFeed('手动喂食');
        }
      }
    });
  },

  // 记录喂食
  recordFeed(source = '手动喂食') {
    const now = new Date();
    const newRecord = {
      id: Date.now(),
      time: now.toISOString(),
      timeStr: this.formatTime(now),
      source: source,
      feeder: '主人' // TODO: 可关联用户昵称
    };

    const records = [newRecord, ...this.data.feedRecords];
    wx.setStorageSync('feed_records', records);

    this.setData({
      feedRecords: records.slice(0, 30),
      todayCount: this.data.todayCount + 1
    });

    wx.showToast({
      title: '喂食已记录',
      icon: 'success'
    });
  },

  // 显示喂食二维码
  showQrCode() {
    this.setData({ showQrModal: true });
  },

  // 关闭二维码弹窗
  closeQrModal() {
    this.setData({ showQrModal: false });
  },

  // 长按保存二维码
  saveQrCode() {
    // 先获取二维码图片临时路径
    const query = wx.createSelectorQuery();
    query.select('#qrCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        const canvas = res[0].node;
        wx.canvasToTempFilePath({
          canvas: canvas,
          success: (fileRes) => {
            wx.saveImageToPhotosAlbum({
              filePath: fileRes.tempFilePath,
              success: () => {
                wx.showToast({ title: '已保存到相册', icon: 'success' });
              },
              fail: (err) => {
                if (err.errMsg.includes('auth')) {
                  wx.showModal({
                    title: '需要授权',
                    content: '请允许保存图片到相册',
                    success: (modalRes) => {
                      if (modalRes.confirm) {
                        wx.openSetting();
                      }
                    }
                  });
                }
              }
            });
          }
        });
      });
  },

  // 分享二维码给好友
  shareQrCode() {
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage']
    });
  },

  onShareAppMessage() {
    return {
      title: '帮旺财喂食',
      path: '/pages/scan/scan?action=feed',
      imageUrl: '' // TODO: 可配置分享图片
    };
  },

  // 清空记录
  clearRecords() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有喂食记录吗？此操作不可恢复。',
      confirmColor: '#FF5722',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('feed_records');
          this.setData({
            feedRecords: [],
            todayCount: 0
          });
          wx.showToast({ title: '已清空', icon: 'success' });
        }
      }
    });
  },

  // 格式化时间
  formatTime(date) {
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const isYesterday = new Date(now - 86400000).toDateString() === date.toDateString();

    const timePart = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

    if (isToday) return `今天 ${timePart}`;
    if (isYesterday) return `昨天 ${timePart}`;

    return `${date.getMonth() + 1}月${date.getDate()}日 ${timePart}`;
  }
});
