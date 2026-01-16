from django.urls import path
from . import views

urlpatterns = [
    # 根路径：GET 列表，POST 上传
    path('', views.songs_root, name='songs-root'),
    
    # 用户自己的歌曲操作
    path('me/', views.get_my_songs, name='get-my-songs'),
    path('<int:song_id>/update/', views.update_my_song, name='update-song'),
    path('<int:song_id>/', views.delete_my_song, name='delete-song'),
    
    # 获取特定歌曲
    path('detail/<int:song_id>/', views.get_song_detail, name='get-song-detail'),
    
    # ==================== 竞标相关路由 ====================
    # 竞标轮次管理
    path('bidding-rounds/', views.bidding_rounds_root, name='bidding-rounds-root'),
    
    # 用户竞标管理
    path('bids/', views.user_bids_root, name='user-bids-root'),
    path('bids/allocate/', views.allocate_bids_view, name='allocate-bids'),
    
    # 竞标结果
    path('bid-results/', views.bid_results_view, name='bid-results'),
]
