// pages/scan/scan.js
// 扫码喂食页面 - 用户扫码后跳转到此页面
Page({
  data: {
    // 页面状态: 'confirming' | 'success' | 'error'
    status: 'confirming',
    // 宠物信息
    petInfo: {
      name: '旺财',
      avatar: '🐕'
    },
    // 是否已记录（防止重复）
    hasRecorded: false,
    // 记录信息
    recordInfo: null
  },

  onLoad(options) {
    // 检查是否是正确的扫码参数
    if (options.action !== 'feed') {
      this.setData({ status: 'error' });
      return;
    }

    // 自动执行喂食记录（也可以改为需要用户点击确认）
    // this.recordFeed();
  },

  // 确认喂食
  confirmFeed() {
    if (this.data.hasRecorded) {
      wx.showToast({ title: '已经记录过了', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '记录中...' });

    // 获取用户信息（需授权）
    wx.getUserProfile({
      desc: '用于记录喂食者信息',
      success: (userRes) => {
        this.doRecordFeed(userRes.userInfo.nickName || '爱心访客');
      },
      fail: () => {
        // 用户拒绝授权，使用默认名称
        this.doRecordFeed('爱心访客');
      }
    });
  },

  // 执行记录
  doRecordFeed(feederName) {
    const now = new Date();
    const newRecord = {
      id: Date.now(),
      time: now.toISOString(),
      timeStr: this.formatTime(now),
      source: '扫码喂食',
      feeder: feederName
    };

    // 读取现有记录
    const records = wx.getStorageSync('feed_records') || [];
    records.unshift(newRecord);
    wx.setStorageSync('feed_records', records);

    // 更新今日计数
    const today = now.toDateString();
    const todayCount = records.filter(r => new Date(r.time).toDateString() === today).length;

    this.setData({
      status: 'success',
      hasRecorded: true,
      recordInfo: {
        ...newRecord,
        todayCount
      }
    });

    wx.hideLoading();

    // 播放成功音效（可选）
    // const innerAudioContext = wx.createInnerAudioContext();
    // innerAudioContext.src = '/audio/success.mp3';
    // innerAudioContext.play();
  },

  // 返回首页
  goHome() {
    wx.switchTab({
      url: '/pages/index/index'
    });
  },

  // 返回宠物页
  goToPet() {
    wx.navigateTo({
      url: '/pages/pet/pet'
    });
  },

  // 格式化时间
  formatTime(date) {
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const timePart = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    if (isToday) return `今天 ${timePart}`;
    return `${date.getMonth() + 1}月${date.getDate()}日 ${timePart}`;
  }
});
