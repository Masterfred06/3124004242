# 论文查重

本项目使用 Python 3 实现论文查重程序。程序从命令行读取原文文件、抄袭版文件和答案文件路径，计算重复率后把结果以两位小数写入答案文件。

## 运行方式

```bash
python main.py <原文文件绝对路径> <抄袭版论文文件绝对路径> <答案文件绝对路径>
```

示例：

```bash
python main.py D:\tests\orig.txt D:\tests\orig_0.8_add.txt D:\tests\ans.txt
```

`requirements.txt` 已提供，但本程序运行不需要安装第三方库。

## 计算模块接口设计

代码分为两个文件：

- `main.py`：命令行入口，只负责接收参数并调用核心模块。
- `plagiarism_checker.py`：查重核心模块，包含文件读取、HTML 正文抽取、文本归一化、n-gram 相似度计算和答案写入。

核心函数：

- `read_text_file(file_path)`：按 `utf-8-sig`、`utf-8`、`gb18030` 顺序读取文本，兼容常见中文文本编码。
- `extract_document_text(raw_text)`：如果输入是普通文本，原样返回；如果是 HTML，则用 `HTMLParser` 抽取正文。对 GitHub blob 页面会优先抽取 `LC` 代码行，避免把导航、脚本、页脚算进论文正文。
- `normalize_text(text)`：统一全角半角、大小写，去掉标点和空白，只保留字母、数字和中文等 Unicode 字母数字字符。
- `calculate_similarity(original_text, suspect_text)`：计算重复率。算法使用字符 1/2/3-gram 频次余弦相似度加权混合，权重分别为 `0.35`、`0.45`、`0.20`。
- `check_documents(original_path, suspect_path)`：读取两个文件并返回最终重复率。
- `write_answer(answer_path, score)`：将结果按 `%.2f` 写入答案文件。
