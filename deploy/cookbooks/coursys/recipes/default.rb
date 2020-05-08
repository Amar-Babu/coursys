ubuntu_mirror = 'https://mirror.its.sfu.ca/mirror/ubuntu/'
ubuntu_release = `lsb_release -c`.split("\t")[1].strip
coursys_dir = node['coursys_dir']
deploy_mode = node['deploy_mode']
username = node['username']
user_home = "/home/#{username}/"

template '/etc/apt/sources.list' do
  variables(
    :mirror => ubuntu_mirror,
    :release => ubuntu_release
  )
  notifies :run, 'execute[apt-get update]', :immediately
end
execute 'apt-get update' do
  action :nothing
end
execute 'apt-get upgrade' do
  command 'apt-get dist-upgrade -y'
  only_if 'apt list --upgradeable | grep -q upgradable'
end


package ['git', 'npm', 'mercurial', 'libmysqlclient-dev', 'python3', 'python3-pip']
if deploy_mode == 'devel'
  package ['sqlite3']
end

execute "install_pip_requirements" do
  command "pip3 install -r #{coursys_dir}/requirements.txt"
end
execute "npm-install" do
  command "npm install"
  cwd coursys_dir
  environment 'HOME' => user_home
  user username
end

# build the locale that a few bits of the system rely on
execute 'build_locale' do
  command 'locale-gen en_CA.UTF-8'
  not_if 'locale -a | grep en_CA.utf8'
end

# ruby for markdown markup
package ['ruby', 'ruby-dev']
execute "github-markdown" do
    command "gem install commonmarker github-markup"
    not_if "ls /usr/local/bin/github-markup"
end
