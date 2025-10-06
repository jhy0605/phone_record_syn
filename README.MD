1、本地修改
git status#                    # 查看文件状态
git diff                       # 查看具体修改内容
git add .                      # 添加所有更改或指定文件 git add 文件名
git commit -m "清晰的修改描述"    # 提交到本地仓库
git push origin 分支名          # 推送到远程仓库

2、远程修改
git pull                  # 拉取远程最新代码
git add 冲突文件
git commit -m "解决冲突"
git push