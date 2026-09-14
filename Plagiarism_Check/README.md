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
