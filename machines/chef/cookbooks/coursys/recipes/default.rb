package "git"
package "libxslt1-dev"
package "python"
package "python-pip"
package "python-dev"
package "python-lxml"
package "sqlite3"
package "zlib1g-dev"

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/"
    command "pip install -r /home/vagrant/courses/build_deps/working_deps.txt"
end

# throw ipython in there: we know it works on the VM
execute "install_ipython" do
    cwd "/home/vagrant/"
    command "pip install ipython"
end

# build the locale that a few bits of the system rely on
execute "build_locale" do
    command "locale-gen en_CA.UTF-8"
end
