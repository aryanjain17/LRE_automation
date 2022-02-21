import os
from os import environ as env
from pathlib import Path
import shutil
import zipfile
import logging
import git
import tempfile
from os import listdir
from os.path import isfile, join


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(funcName)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("process")
logger.setLevel("DEBUG")


for k, v in env.items():
    logger.debug(f"{k}={v}")
LRE_SCRIPTS_PATH = "PAT/Digital/scripts/"
TEMP_DIR_ADDRESS = "source.txt"
logger.debug("lre scripts are located at %s" % (LRE_SCRIPTS_PATH))


def difference(s1, s2):
    index = s1.find(s2)
    if index != -1 and index + len(s2) < len(s1):
        logger.debug("%s is found at position %s" % (s2, index))
        # get the filename of update
        return s1[index + len(s2) :]
    else:
        return None


def check_the_updates():
    # See the latest git push
    repo = git.Repo()
    output = []
    # Difference between last 2 commits
    diff = repo.git.diff("HEAD~1..HEAD", name_only=True).split()
    logger.info("git diff is calculated.")
    logger.debug("latest updates are: %s" % (diff))
    scriptpath = LRE_SCRIPTS_PATH
    logger.debug("PAT scripts are at %s" % (scriptpath))
    for item in diff:
        logger.debug("%s is committed" % (item))
        if scriptpath in item:
            dirpath = difference(item, scriptpath).split("/")[0].split(" ")[0]
            logger.info("This is the zip file name %s" % (dirpath))
            logger.info("This is the item name %s" % (item))
            temp = {dirpath: item}
            output.append(temp)
            logger.debug(temp)
    logger.debug("all the updates are %s" % (output))
    return output


def tempdir():
    dirpath = tempfile.mkdtemp()
    logger.debug("%s is created" % dirpath)
    with open(TEMP_DIR_ADDRESS, "w") as text_file:
        text_file.write(dirpath)
        print(f"##vso[task.setvariable variable=zip_dir;isOutput=true]{dirpath}")
        logger.debug(f"Pipeline variable ZIP_DIR is set to {dirpath}")
        logger.debug("temp dir is recorded into %s" % text_file.name)
    return dirpath


# loop on all Directories under Output dir zip them one by one
def zip_items(input_items):
    temp = Path(tempdir())
    onlyfiles = [f for f in listdir(temp) if isfile(join(temp, f))]
    print(f'All files in the temp directory: {onlyfiles}')
    logger.debug("%s is the temp dir." % temp)
    zips = []
    for item in input_items:
        for k in item:
            Path(temp / k).mkdir(parents=True, exist_ok=True)
            source = item[k]
            destination = (temp / k / Path(item[k]).name)
            print(f' Source : {source} ,  Destination : {destination}')
            src_files = os.listdir(os.path.dirname(os.path.abspath(source)))
            # Copy all files in the location where change is identified to the tmp location
            for file_name in src_files:
                full_file_name = os.path.join(os.path.dirname(os.path.abspath(source)), file_name)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, os.path.dirname(os.path.abspath(destination)))
            ret = shutil.copy(item[k], temp / k / Path(item[k]).name)
            logger.debug("%s is copied to %s " % (item[k], ret))
            zips.append(temp / k)
    os.chdir(temp)
    logger.debug("working directory is changed to %s" % temp)
    for to_zip in set(zips):
        zipdir(to_zip)


# Function to Zip a directory
def zipdir(dirpath):
    zipname = dirpath.name
    logger.debug("%s is the zip name." % zipname)
    zipf = zipfile.ZipFile(zipname + ".zip", "w", zipfile.ZIP_DEFLATED)
    for base, dirs, files in os.walk(dirpath):
        for z_file in files:
            zipf.write(zipname + "/" + z_file)
            logger.debug("%s is zipped" % z_file)
    zipf.close()
    logger.debug("%s is the zip file" % zipf.filename)
    logger.debug("testing the file %s" % zipf.namelist())


if __name__ == "__main__":
    logger.info("Triggered, the latest push will be checked.")
    try:
        lre_script_updates = check_the_updates()
        if lre_script_updates:
            logger.info("LRE script updates found, will zip and upload")
            zip_items(lre_script_updates)

        else:
            logger.info("no LRE scipt update")
    except Exception:
        #logger.exception("Fatal error in main loop")
        logger.error('Fatal error in main loop: '+ str(Exception))
