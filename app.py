import io
import os
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from flask import Flask, request, jsonify, render_template_string


def configure_chinese_font():
    font_candidates = [
        'Microsoft YaHei',
        'SimHei',
        'SimSun',
        'KaiTi',
        'FangSong',
        'Arial Unicode MS',
        'PingFang SC',
        'Noto Sans CJK SC',
        'WenQuanYi Zen Hei',
        'Source Han Sans CN',
    ]

    available_fonts = {f.name for f in font_manager.fontManager.ttflist}

    for font_name in font_candidates:
        if font_name in available_fonts:
            plt.rcParams['font.sans-serif'] = [font_name]
            plt.rcParams['axes.unicode_minus'] = False
            return font_name

    font_dirs = [
        os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'),
        '/System/Library/Fonts',
        '/usr/share/fonts',
    ]

    for font_dir in font_dirs:
        if os.path.isdir(font_dir):
            for file in os.listdir(font_dir):
                if file.lower().endswith(('.ttf', '.ttc', '.otf')):
                    if any(kw in file.lower() for kw in ['yahei', 'simhei', 'simsun', 'pingfang', 'noto', 'cjk', 'wqy']):
                        try:
                            font_path = os.path.join(font_dir, file)
                            font_manager.fontManager.addfont(font_path)
                            font_name = font_manager.FontProperties(fname=font_path).get_name()
                            plt.rcParams['font.sans-serif'] = [font_name]
                            plt.rcParams['axes.unicode_minus'] = False
                            return font_name
                        except Exception:
                            continue

    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    return None


configure_chinese_font()

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>饼图生成服务</title>
    <style>
        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .data-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            align-items: center;
        }
        .data-row input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .data-row input[type="text"] {
            flex: 1;
        }
        .data-row input[type="number"] {
            width: 120px;
        }
        .data-row button {
            background: #ff4d4f;
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 5px;
            cursor: pointer;
        }
        .actions {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .actions button {
            padding: 10px 20px;
            font-size: 14px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .btn-add {
            background: #1890ff;
            color: white;
        }
        .btn-generate {
            background: #52c41a;
            color: white;
        }
        .result {
            margin-top: 30px;
            text-align: center;
        }
        .result img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .error {
            color: #ff4d4f;
            margin-top: 10px;
            padding: 10px;
            background: #fff1f0;
            border-radius: 5px;
        }
        .options {
            margin: 20px 0;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
            border: 1px solid #eee;
        }
        .options h4 {
            margin: 0 0 12px 0;
            color: #333;
        }
        .option-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        .option-row:last-child {
            margin-bottom: 0;
        }
        .option-row label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 14px;
            color: #444;
        }
        .option-row input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .option-row input[type="range"] {
            width: 200px;
            cursor: pointer;
        }
        .option-value {
            font-weight: bold;
            color: #1890ff;
            min-width: 40px;
        }
        .option-hint {
            font-size: 12px;
            color: #888;
        }
    </style>
</head>
<body>
    <h1>饼图生成服务</h1>
    <div class="container">
        <h3>输入分类和数值：</h3>
        <div id="data-rows">
            <div class="data-row">
                <input type="text" placeholder="分类名称" value="分类A">
                <input type="number" placeholder="数值" value="30" min="0">
                <button onclick="removeRow(this)">删除</button>
            </div>
            <div class="data-row">
                <input type="text" placeholder="分类名称" value="分类B">
                <input type="number" placeholder="数值" value="45" min="0">
                <button onclick="removeRow(this)">删除</button>
            </div>
            <div class="data-row">
                <input type="text" placeholder="分类名称" value="分类C">
                <input type="number" placeholder="数值" value="25" min="0">
                <button onclick="removeRow(this)">删除</button>
            </div>
        </div>

        <div class="options">
            <h4>📐 图表选项</h4>
            <div class="option-row">
                <label>
                    <input type="checkbox" id="donut-mode" checked onchange="toggleDonutOptions()">
                    <strong>环形图模式</strong> <span class="option-hint">(中心留白，更美观)</span>
                </label>
            </div>
            <div class="option-row" id="donut-size-row">
                <label>中心留白大小：</label>
                <input type="range" id="hole-size" min="30" max="85" value="70" oninput="updateHoleSizeDisplay()">
                <span class="option-value" id="hole-size-value">70%</span>
            </div>
        </div>

        <div class="actions">
            <button class="btn-add" onclick="addRow()">+ 添加一行</button>
            <button class="btn-generate" onclick="generatePie()">生成饼图</button>
        </div>
        <div id="error" class="error" style="display:none;"></div>
        <div id="result" class="result"></div>
    </div>

    <script>
        function addRow() {
            const container = document.getElementById('data-rows');
            const row = document.createElement('div');
            row.className = 'data-row';
            row.innerHTML = `
                <input type="text" placeholder="分类名称">
                <input type="number" placeholder="数值" min="0">
                <button onclick="removeRow(this)">删除</button>
            `;
            container.appendChild(row);
        }

        function removeRow(btn) {
            const rows = document.querySelectorAll('#data-rows .data-row');
            if (rows.length <= 1) {
                alert('至少保留一行数据');
                return;
            }
            btn.parentElement.remove();
        }

        function generatePie() {
            const rows = document.querySelectorAll('#data-rows .data-row');
            const labels = [];
            const values = [];

            for (const row of rows) {
                const inputs = row.querySelectorAll('input');
                const label = inputs[0].value.trim();
                const value = parseFloat(inputs[1].value);

                if (!label) {
                    showError('请填写所有分类名称');
                    return;
                }
                if (isNaN(value) || value < 0) {
                    showError('请填写有效的数值（大于等于0）');
                    return;
                }
                labels.push(label);
                values.push(value);
            }

            const total = values.reduce((a, b) => a + b, 0);
            if (total <= 0) {
                showError('所有数值之和必须大于0');
                return;
            }

            hideError();
            document.getElementById('result').innerHTML = '<p>正在生成...</p>';

            const chartOptions = getChartOptions();

            fetch('/api/pie', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ labels, values, ...chartOptions })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('result').innerHTML =
                        '<img src="data:image/png;base64,' + data.image + '" alt="饼图">';
                } else {
                    showError(data.error || '生成失败');
                }
            })
            .catch(err => showError('请求失败：' + err.message));
        }

        function showError(msg) {
            const el = document.getElementById('error');
            el.textContent = msg;
            el.style.display = 'block';
            document.getElementById('result').innerHTML = '';
        }

        function hideError() {
            document.getElementById('error').style.display = 'none';
        }

        function toggleDonutOptions() {
            const donutChecked = document.getElementById('donut-mode').checked;
            const sizeRow = document.getElementById('donut-size-row');
            sizeRow.style.opacity = donutChecked ? '1' : '0.4';
            sizeRow.style.pointerEvents = donutChecked ? 'auto' : 'none';
        }

        function updateHoleSizeDisplay() {
            const value = document.getElementById('hole-size').value;
            document.getElementById('hole-size-value').textContent = value + '%';
        }

        function getChartOptions() {
            const donut = document.getElementById('donut-mode').checked;
            const holeSize = parseInt(document.getElementById('hole-size').value) / 100;
            return { donut, hole_size: holeSize };
        }
    </script>
</body>
</html>
"""


def merge_small_categories(labels, values, threshold=0.05):
    total = sum(values)
    if total <= 0:
        return labels, values

    merged_labels = []
    merged_values = []
    other_value = 0.0

    for label, value in zip(labels, values):
        if value / total < threshold:
            other_value += value
        else:
            merged_labels.append(label)
            merged_values.append(value)

    if other_value > 0:
        merged_labels.append('其他')
        merged_values.append(other_value)

    if len(merged_labels) < 2:
        return labels, values

    return merged_labels, merged_values


def generate_pie_chart(labels, values, donut=True, hole_size=0.70):
    labels, values = merge_small_categories(labels, values)

    if hole_size < 0.3:
        hole_size = 0.3
    elif hole_size > 0.85:
        hole_size = 0.85

    fig, ax = plt.subplots(figsize=(8, 6))

    colors = plt.cm.Set3.colors
    if len(labels) > len(colors):
        colors = plt.cm.tab20.colors

    if donut:
        wedgeprops = {'width': 1.0 - hole_size, 'edgecolor': 'white', 'linewidth': 2}
        pctdistance = hole_size + (1.0 - hole_size) * 0.5
    else:
        wedgeprops = {'edgecolor': 'white', 'linewidth': 1}
        pctdistance = 0.75

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors[:len(labels)],
        pctdistance=pctdistance,
        textprops={'fontsize': 12},
        wedgeprops=wedgeprops
    )

    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontweight('bold')

    ax.axis('equal')

    if donut:
        ax.set_title('数据分布环形图', fontsize=16, fontweight='bold', pad=20)
    else:
        ax.set_title('数据分布饼图', fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode('utf-8')


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/pie', methods=['POST'])
def api_pie():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供JSON数据'}), 400

        labels = data.get('labels', [])
        values = data.get('values', [])

        if not labels or not values:
            return jsonify({'success': False, 'error': '请提供 labels 和 values 数组'}), 400

        if len(labels) != len(values):
            return jsonify({'success': False, 'error': 'labels 和 values 长度必须一致'}), 400

        if len(labels) < 2:
            return jsonify({'success': False, 'error': '至少需要2个分类'}), 400

        values = [float(v) for v in values]
        if sum(values) <= 0:
            return jsonify({'success': False, 'error': '所有数值之和必须大于0'}), 400

        donut = data.get('donut', True)
        hole_size = float(data.get('hole_size', 0.70))

        image_base64 = generate_pie_chart(labels, values, donut=donut, hole_size=hole_size)
        return jsonify({'success': True, 'image': image_base64})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
