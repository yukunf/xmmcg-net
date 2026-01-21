from django.urls import path
from . import views

urlpatterns = [
    # ==================== 首页展示数据 ====================
    path('banners/', views.get_banners, name='banners'),
    path('announcements/', views.get_announcements, name='announcements'),
    path('status/', views.get_competition_status, name='competition-status'),
    path('phases/', views.get_competition_phases, name='competition-phases'),
    path('phase/current/', views.get_current_phase, name='current-phase'),
    
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
    path('bidding-rounds/<int:round_id>/available-charts/', views.get_available_charts_for_round, name='available-charts'),
    path('bidding-rounds/auto-create-chart-round/', views.auto_create_chart_bidding_round, name='auto-create-chart-round'),
    
    # 用户竞标管理
    path('bids/', views.user_bids_root, name='user-bids-root'),
    path('bids/<int:bid_id>/', views.delete_bid_view, name='delete-bid'),
    path('bids/target/', views.target_bids_list, name='target_bids_list'),
    path('bids/allocate/', views.allocate_bids_view, name='allocate-bids'),
    
    # 竞标结果
    path('bid-results/', views.bid_results_view, name='bid-results'),
    
    # ==================== 谱面相关路由 ====================
    path('charts/', views.charts_root, name='charts-root'),
    path('charts/me/', views.get_user_charts, name='get-user-charts'),
    path('charts/<int:result_id>/submit/', views.submit_chart, name='submit-chart'),
    path('charts/<int:chart_id>/bundle/', views.download_chart_bundle, name='download-chart-bundle'),
    path('charts/<int:chart_id>/reviews/', views.get_chart_reviews, name='get-chart-reviews'),
    
    # ==================== 互评相关路由 ====================
    path('peer-reviews/allocate/<int:round_id>/', views.allocate_peer_reviews, name='allocate-peer-reviews'),
    path('peer-reviews/tasks/', views.get_peer_review_tasks, name='get-peer-review-tasks'),
    path('peer-reviews/allocations/<int:allocation_id>/submit/', views.submit_peer_review, name='submit-peer-review'),
    path('peer-reviews/extra/', views.submit_extra_peer_review, name='submit-extra-peer-review'),
    
    # ==================== 排名相关路由 ====================
    path('rankings/<int:round_id>/', views.get_round_rankings, name='get-round-rankings'),
    
    
    # ==================== 第二轮竞标相关路由（已废弃，使用统一的竞标系统） ====================
    # 注意：以下路由已被注释，现在使用统一的Bid系统来处理谱面竞标
    # path('second-bidding-rounds/', views.second_bidding_rounds, name='second-bidding-rounds'),
    # path('second-bidding-rounds/<int:second_round_id>/available-charts/', views.available_charts_for_second_bidding, name='available-charts'),
    # path('second-bids/', views.submit_second_bid, name='submit-second-bid'),
    # path('second-bidding-rounds/<int:second_round_id>/my-bids/', views.get_user_second_bids, name='get-user-second-bids'),
    # path('second-bidding-rounds/<int:second_round_id>/allocate/', views.allocate_second_bids, name='allocate-second-bids'),
    # path('second-bidding-rounds/<int:second_round_id>/my-results/', views.get_second_bid_results, name='get-second-bid-results'),
]