package "git"
package "libxslt1-dev"
package "python3"
#package "python3-pip"
package "python3-setuptools"
package "python3-dev"
package "python3-lxml"
package "sqlite3"
package "zlib1g-dev"
package "libjpeg8-dev" # for pillow build
package "mercurial"
package "build-essential"


#install the proper pip
execute "install_proper_pip" do
    command "easy_install3 pip"
end

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/ubuntu/"
    command "pip3 install -r /home/ubuntu/courses/requirements.txt"
end

# throw ipython in there: we know it works on the VM
execute "install_ipython" do
    cwd "/home/ubuntu/"
    command "pip3 install ipython"
end

# build the locale that a few bits of the system rely on
execute "build_locale" do
    command "locale-gen en_CA.UTF-8"
end

package ['ruby', 'ruby-dev']
execute "github-markdown" do
    command "gem install commonmarker github-markup"
    not_if "ls /usr/local/bin/github-markup"
end
