import yaml, logging, shutil, os

def parse_config(config_file, required_keys):
    with open(config_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logging.error(exc)
   
    for key in required_keys:
        if key not in config:
            logging.error("key %s not found" % key)
            exit(1)

    logging.info("config %s pass" % config_file)
    return config

def instantiate_module(module_name, instance_name, project_id, template):
    # read the data
    with open(template, 'r') as file :
        filedata = file.read()

    # replace the target strings
    filedata = filedata.replace('MODULE_NAME', module_name)
    filedata = filedata.replace('INSTANCE_NAME', instance_name)
    filedata = filedata.replace('PROJECT_ID', str(project_id))

    # return the string
    return filedata

def add_instance_to_upw(macro_verilog, user_project_wrapper_path, upw_template):
    # read the data
    with open(upw_template, 'r') as file :
        filedata = file.read()

    # replace the target strings
    filedata = filedata.replace('MODULE_INSTANCES', macro_verilog)

    # overwrite the upw
    logging.info("writing to %s" % user_project_wrapper_path)
    with open(user_project_wrapper_path, 'w') as file:
        file.write(filedata)

def try_copy(src, dst, force_delete):
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
