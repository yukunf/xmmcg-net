"""
Django management command to automatically update CompetitionPhase is_active status based on time.

Usage:
    python manage.py update_phase_status

This command should be run periodically (e.g., via cron job or scheduled task) to ensure
that is_active reflects the actual phase status based on start_time and end_time.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from songs.models import CompetitionPhase


class Command(BaseCommand):
    help = '根据时间自动更新 CompetitionPhase 的 is_active 状态'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要修改的阶段，不实际修改数据库',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        # 获取所有阶段
        all_phases = CompetitionPhase.objects.all()
        
        updated_count = 0
        activated_phases = []
        deactivated_phases = []
        
        for phase in all_phases:
            # 计算应该的状态：正在进行中的阶段应该是 active
            should_be_active = (phase.start_time <= now <= phase.end_time)
            current_is_active = phase.is_active
            
            # 如果状态需要改变
            if should_be_active != current_is_active:
                if dry_run:
                    # 干运行模式：只记录变化
                    if should_be_active:
                        activated_phases.append(phase)
                        self.stdout.write(
                            self.style.SUCCESS(f'[DRY RUN] 将激活: {phase.name} (phase_key: {phase.phase_key})')
                        )
                    else:
                        deactivated_phases.append(phase)
                        self.stdout.write(
                            self.style.WARNING(f'[DRY RUN] 将停用: {phase.name} (phase_key: {phase.phase_key})')
                        )
                else:
                    # 实际更新
                    phase.is_active = should_be_active
                    phase.save(update_fields=['is_active'])
                    updated_count += 1
                    
                    if should_be_active:
                        activated_phases.append(phase)
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ 已激活: {phase.name} (phase_key: {phase.phase_key})')
                        )
                    else:
                        deactivated_phases.append(phase)
                        self.stdout.write(
                            self.style.WARNING(f'✓ 已停用: {phase.name} (phase_key: {phase.phase_key})')
                        )
        
        # 输出总结
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.NOTICE('【干运行模式 - 未实际修改数据库】'))
            self.stdout.write(f'将激活 {len(activated_phases)} 个阶段')
            self.stdout.write(f'将停用 {len(deactivated_phases)} 个阶段')
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ 成功更新 {updated_count} 个阶段'))
            self.stdout.write(f'激活: {len(activated_phases)} 个')
            self.stdout.write(f'停用: {len(deactivated_phases)} 个')
        
        # 显示当前活跃的阶段
        current_active_phases = CompetitionPhase.objects.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        )
        
        self.stdout.write('\n当前活跃阶段:')
        if current_active_phases.exists():
            for phase in current_active_phases:
                self.stdout.write(
                    self.style.SUCCESS(f'  • {phase.name} ({phase.phase_key})')
                )
        else:
            self.stdout.write(self.style.WARNING('  (无)'))
        
        self.stdout.write('=' * 60)
