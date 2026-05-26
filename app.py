<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Straw System - NVDA</title>

<style>
body{
    margin:0;
    background:#0b0f17;
    font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial;
    color:#e5e7eb;
    display:flex;
    justify-content:center;
    padding:40px;
}

.card{
    width:460px;
    background:#111827;
    border:1px solid #263041;
    border-radius:14px;
    padding:18px 18px 14px 18px;
    box-shadow:0 10px 30px rgba(0,0,0,0.45);
}

.title{
    font-size:15px;
    font-weight:700;
    margin-bottom:10px;
}

.symbol{
    color:#93c5fd;
    font-weight:700;
}

.metric{
    margin-top:10px;
    font-size:13px;
    color:#cbd5e1;
    line-height:1.6;
}

.small{
    margin-top:8px;
    font-size:12px;
    color:#94a3b8;
    line-height:1.5;
}

.status{
    margin-top:12px;
    padding:10px;
    border-radius:10px;
    background:#0f172a;
    border:1px solid #263041;
    font-weight:700;
}

.warn{
    color:#fbbf24;
}

.good{
    color:#34d399;
}

.badge{
    display:inline-block;
    padding:2px 8px;
    border-radius:999px;
    font-size:11px;
    background:#1f2937;
    color:#e5e7eb;
    margin-left:6px;
}
</style>
</head>

<body>

<div class="card">

    <div class="title">
        Symbol：<span class="symbol">NVDA</span>
    </div>

    <div class="title">
        🧨 稻草一：AI资本开支循环检测
    </div>

    <div id="status" class="status">
        当前状态：计算中...
    </div>

    <div class="metric">
        核心判断：资本开支扩张速度 vs 收入增长速度
    </div>

    <div class="small">
        规则：当 CapEx 增速 > 收入增速 × 1.2 → 资本开支过热信号
    </div>

    <div class="metric">
        收入增速：<span id="rev">65.47</span>% ｜ 
        CapEx增速：<span id="capex">86.71</span>%
    </div>

    <div class="small" id="calc"></div>

</div>

<script>
// ===== 数据 =====
const revenueGrowth = 65.47;
const capexGrowth = 86.71;

// ===== 规则 =====
const threshold = revenueGrowth * 1.2;
const isOverheat = capexGrowth > threshold;

// ===== UI 更新 =====
const status = document.getElementById("status");
const calc = document.getElementById("calc");

// 状态显示
if (isOverheat) {
    status.innerHTML = "当前状态：🟡 过热风险 <span class='badge'>HOT</span>";
    status.classList.add("warn");
} else {
    status.innerHTML = "当前状态：🟢 正常区间 <span class='badge'>OK</span>";
    status.classList.add("good");
}

// 计算过程展示
calc.innerHTML =
    "计算：CapEx " + capexGrowth +
    " vs 阈值 " + threshold.toFixed(2) +
    "（收入 × 1.2） → " +
    (isOverheat ? "触发过热信号" : "未触发风险");
</script>

</body>
</html>
