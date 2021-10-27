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

    if os.path.exists(repo_dir):
        if force_delete:
            logging.warning("deleting %s" % repo_dir)
            shutil.rmtree(repo_dir)
        else:
            logging.warning("directory already exists - skipping. Use --force-delete to remove")
            return

    logging.info("cloning %s" % repo_url)
    repo = git.Repo.clone_from(repo_url, repo_dir)
    logging.info("checking out to %s" % commit)
    repo.git.checkout(commit)

    logging.info("installing submodules")
    # the submodule support for gitpython is broken, so use git (via repo) to do the work instead.
    repo.git.submodule('update', '--init', '--recursive')

