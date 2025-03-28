# 1. Clone it into a folder
git clone https://github.com/someone/their-repo.git my-folder-name

# 2. Go into that folder
cd my-folder-name

# 3. Remove its .git directory to strip Git history
rm -rf .git

# 4. Go back to your main repo
cd ..

# 5. Add it to your repo like any normal folder
git add my-folder-name
git commit -m "Added code from their-repo as a normal folder"
git push
