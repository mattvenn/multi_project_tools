import logging
import os
import shutil
import yaml
import git


def parse_config(config_file, required_keys):
    with open(config_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logging.error(exc)
   
    for key in required_keys:
        if key not in config:
            logging.error("key %s not found in %s" % (key, config_file))
            exit(1)

    logging.debug("config %s pass" % config_file)
    return config


def add_verilog_includes(projects, upw_includes_path, upw_includes_template, gl=False):
    with open(upw_includes_template, 'r') as file:
        filedata = file.read()

    gl_includes = ""
    project_includes = ""
    for project in projects:
        project_includes += ("// %s\n" % project)
        for path in project.get_module_source_paths(absolute=False):
            path = os.path.join(os.path.basename(project.directory), path)
            project_includes += ('	`include "%s"\n' % path)

        
        gl_includes += ('`include "gl/%s"\n' % project.config['gds']['lvs_filename'])

    # TODO
    # GL is broken in caravel, so can't use this file the way it's meant to be used. 
    # Setting GL in the Makefile will always die until the GL of Caravel is fixed
    # So instead, put the GL includes in the RTL includes, and don't set GL
    filedata = filedata.replace('GL_INCLUDES',  "")
    if gl == True:
        filedata = filedata.replace('RTL_INCLUDES', gl_includes)
    else:
        filedata = filedata.replace('RTL_INCLUDES', project_includes)


    # overwrite the includes
    logging.info("writing to %s" % upw_includes_path)
    with open(upw_includes_path, 'w') as file:
        file.write(filedata)


def add_instance_to_upw(macro_verilog, user_project_wrapper_path, upw_template):
    # read the data
    logging.info("instantiating macro inside upw")
    with open(upw_template, 'r') as file:
        filedata = file.read()

    # replace the target strings
    filedata = filedata.replace('MODULE_INSTANCES', macro_verilog)

    # overwrite the upw
    logging.info("writing to %s" % user_project_wrapper_path)
    with open(user_project_wrapper_path, 'w') as file:
        file.write(filedata)


def try_copy_tree(src, dst, force_delete):
    logging.info("copying %s to %s" % (src, dst))
    try:
        shutil.copytree(src, dst)
    except FileExistsError as e:
        if force_delete:
            logging.warning("deleting %s" % dst)
            shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            logging.error(e)
            logging.info("use --force-delete to remove old directories")
            exit(1)


def try_mkdir(dst, force_delete):
    try:
        os.mkdir(dst)
    except FileExistsError as e:
        if force_delete:
            logging.warning("deleting %s" % dst)
            shutil.rmtree(dst)
            os.mkdir(dst)
        else:
            logging.error(e)
            logging.info("use --force-delete to remove old directories")
            exit(1)


def clone_repo(repo_url, commit, repo_dir, force_delete):

    if os.path.exists(repo_dir) and force_delete:
        logging.warning("deleting %s" % repo_dir)
        shutil.rmtree(repo_dir)

    logging.info("cloning %s" % repo_url)
    repo = git.Repo.clone_from(repo_url, repo_dir)
    logging.info("checking out to %s" % commit)
    repo.git.checkout(commit)

    logging.info("installing submodules")
    # the submodule support for gitpython is broken, so use git (via repo) to do the work instead.
    repo.git.submodule('update', '--init', '--recursive')

