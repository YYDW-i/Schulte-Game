def schulte_level(adjusted_seconds: float) -> tuple[str, str]:
    s = adjusted_seconds

    if s < 15:
        return "世界级（World Class）", "你已经很强了：可以挑战 6×6、倒序、或加入干扰条件（噪声/计数）保持稳定。"
    if s < 25:
        return "专家（Expert）", "目标：把波动压小（更稳），并保持 0 错或极低错误率。"
    if s < 35:
        return "高级（Advanced）", "很不错：建议练“中心凝视+余光分区”，把 25 秒内稳定下来。"
    if s < 50:
        return "中级（Intermediate）", "处在常见练习区间：先稳准（0错）再提速，避免乱扫。"
    if s < 90:
        return "入门（Beginner）", "建议先形成固定策略：分区找数、减少回看，慢一点但不出错。"
    return "需要加强", "先把目标定在 60–90 秒：专注完成 + 0错优先，稳定后自然会提速。"

def training_tips() -> list[str]:
    return [
        "盯住中心格，用余光覆盖全表，减少逐格扫视。",  # 常见训练要点来源于多款训练工具描述
        "先追求 0 错，再追求速度；错误越多越影响有效训练。",
        "每次训练建议控制轮数，避免疲劳导致动作变形。",
    ]
