"""Stage gates for recorded creative work; no automatic aesthetic judgement."""
from datetime import datetime
import math

STAGES = ('script', 'director', 'edit', 'final')
REVIEW_KEYS = ('opening', 'rhythm', 'captions', 'voice', 'music', 'transitions')


def obj(value):
    return value if isinstance(value, dict) else {}


def rows(value):
    return value if isinstance(value, list) else []


def text(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    try:
        return text(value) and datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset() is not None
    except ValueError:
        return False


def validate_creative(data, stage='auto'):
    errors = []
    editing = obj(data.get('editing'))
    script = obj(data.get('script'))
    director = obj(data.get('director'))
    if stage == 'auto':
        if editing.get('status') == 'qa_pass' or obj(data.get('delivery')).get('status') == 'ready':
            stage = 'final'
        elif editing.get('status') == 'rendered':
            stage = 'edit'
        else:
            return errors
    if stage not in STAGES:
        return ['未知创意检查阶段']
    required = 'final' if editing.get('status') == 'qa_pass' or obj(data.get('delivery')).get('status') == 'ready' else 'edit' if editing.get('status') == 'rendered' else stage
    level = max(STAGES.index(stage), STAGES.index(required))

    def require(condition, message):
        if not condition:
            errors.append('创意门槛: ' + message)

    candidates = rows(script.get('hook_candidates'))
    require(len(candidates) >= 3, '需要至少三种开头钩子')
    ids, kinds, texts = set(), set(), set()
    selected = None
    for index, value in enumerate(candidates):
        hook = obj(value)
        for key in ('hook_id', 'kind', 'text', 'visual_proof', 'appeal_reason'):
            require(text(hook.get(key)), f'钩子{index + 1}缺少 {key}')
        hook_id = hook.get('hook_id')
        if text(hook_id):
            require(hook_id not in ids, 'hook_id 不得重复')
            ids.add(hook_id)
        if text(hook.get('kind')):
            kinds.add(hook['kind'].strip())
        if text(hook.get('text')):
            texts.add(hook['text'].strip())
        require(hook.get('proof_status') in ('ready', 'pending'), '钩子 proof_status 无效')
        if text(hook_id) and hook_id == script.get('selected_hook_id'):
            selected = hook
    require(len(kinds) >= 3 and len(texts) >= 3, '开头需有三种不同类型和文案')
    require(selected is not None, 'selected_hook_id 必须引用候选钩子')
    require(text(script.get('selection_reason')), '缺少钩子选择理由')
    if selected:
        require(script.get('hook') == selected.get('text'), 'hook 与选中钩子不一致')
    beats = rows(script.get('beats'))
    require(len(beats) >= 2, '需要分段口播及情绪停顿设计')
    emotions, has_pause = set(), False
    for value in beats:
        beat = obj(value)
        require(text(beat.get('text')) and text(beat.get('emotion')), '口播缺少文字或情绪')
        if text(beat.get('emotion')):
            emotions.add(beat['emotion'].strip())
        pause = beat.get('pause_after_ms')
        valid_pause = isinstance(pause, (int, float)) and not isinstance(pause, bool) and math.isfinite(pause) and pause >= 0
        require(valid_pause, '停顿必须是非负毫秒数')
        has_pause = has_pause or (valid_pause and pause > 0)
    require(len(emotions) >= 2 and has_pause, '口播需要情绪变化和停顿')
    if level < 1:
        return errors
    shots = rows(director.get('shots'))
    require(bool(shots), '缺少逐镜头声画设计')
    for index, value in enumerate(shots):
        shot = obj(value)
        for key in ('visual_source', 'caption', 'caption_style', 'motion', 'transition', 'music', 'sfx', 'voice_emotion'):
            require(text(shot.get(key)), f'镜头{index + 1}缺少 {key}')
    first = obj(shots[0]) if shots else {}
    require(first.get('start') == 0 and first.get('opening_result') is True, '前三秒必须从真实结果画面开始')
    if level < 2:
        return errors
    require(bool(selected) and selected.get('proof_status') == 'ready', '剪辑前选中钩子的真实画面必须就绪')
    engine = editing.get('engine')
    if engine != 'jianying_desktop':
        override = obj(editing.get('engine_override'))
        require(text(engine) and override.get('engine') == engine and all(text(override.get(k)) for k in ('reason', 'user_instruction')), '默认桌面剪映；其他引擎必须记录用户明确选择')
    preflight = obj(editing.get('preflight'))
    require(preflight.get('status') == 'passed', '剪辑前实际操作/免费资源检查未通过')
    require(timestamp(preflight.get('checked_at')), '资源检查时间必须带时区')
    require(text(preflight.get('app_version')) and text(preflight.get('operation_evidence')), '缺少软件版本和实际操作证据')
    resources = rows(preflight.get('resources'))
    categories = set()
    for value in resources:
        resource = obj(value)
        if text(resource.get('kind')):
            categories.add(resource['kind'])
        require(resource.get('free') is True, '资源未证实免费')
        require(resource.get('license_status') == 'verified', '资源许可必须实际核验为 verified')
        scope = resource.get('license_scope')
        require(text(scope) and scope.strip().lower() not in {'unknown', 'pending', 'n/a', 'tbd', '未知', '待确认', '待核验', '未核验'}, '许可范围不能是未知或待确认占位值')
        for key in ('name', 'license_scope', 'evidence'):
            require(text(resource.get(key)), f'资源缺少 {key}')
        require(timestamp(resource.get('checked_at')), '资源取证时间必须带时区')
    require({'voice', 'caption', 'transition', 'music', 'sfx'} <= categories, '需检查配音/花字/转场/音乐/音效五类资源')
    require(editing.get('status') != 'blocked', '剪映受阻，必须报告 blocker/recovery_action 后停止')
    if level < 3:
        return errors
    require(editing.get('status') == 'qa_pass', '最终交付需要 editing.status=qa_pass')
    require(text(editing.get('export_evidence')), '缺少实际软件导出证据')
    review = obj(editing.get('creative_review'))
    require(review.get('status') == 'passed', '创意质量未通过，需返工并重新看听')
    require(text(review.get('reviewer')) and timestamp(review.get('reviewed_at')), '创意验收需检查人和带时区的时间')
    require(text(review.get('render_path')) and review.get('render_path') == editing.get('render_path'), '创意验收必须对应当前导出文件')
    digest = review.get('render_sha256')
    require(isinstance(digest, str) and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), '创意验收需记录当前成片 SHA256')
    checks = obj(review.get('checks'))
    for key in REVIEW_KEYS:
        check = obj(checks.get(key))
        require(check.get('status') == 'passed' and text(check.get('evidence')) and check.get('issues') == [], f'{key} 未通过或缺少时间码/观察记录')
    require(isinstance(editing.get('rework_log', []), list), 'rework_log 必须是数组')
    for value in rows(editing.get('rework_log')):
        item = obj(value)
        require(item.get('status') == 'resolved' and text(item.get('issue')) and text(item.get('action')), '尚有未完成或无记录的返工项')
    return errors
