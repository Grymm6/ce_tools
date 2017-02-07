import os
import platform
import subprocess


# Group these here for transparency and easy editing.
USED_REPOSITORY = 'CRYENGINE'
USED_TARGET = 'win_x86'
USED_CONFIG = 'Profile'
USED_BRANCH = 'release'
USED_VS_VERSION = '14.0'

TARGET_TO_SLN_TAG = {
    'win_x86': 'Win32',
    'win_x64': 'Win64'
}


def get_installed_vs_versions():
    """
    Query the registry to find installed VS versions. Assumes that C++ support has been installed.
    Throws an exception if the expected version of VS is not present.
    :return: None
    """
    import winreg

    # Open the Visual Studio registry key.
    reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    vskey = winreg.OpenKey(reg, r'SOFTWARE\Microsoft\VisualStudio')

    subkeys = []

    # Read all the subkeys
    try:
        i = 0
        while True:
            subkeys.append(winreg.EnumKey(vskey, i))
            i += 1
    except OSError:
        pass

    # If a subkey includes '.0' it's almost certainly a version number. I've yet to see one without that.
    available_versions = [version for version in subkeys if '.0' in version]

    if USED_VS_VERSION not in available_versions:
        raise OSError('Visual Studio version {} is not installed (available: {}).'.format(USED_VS_VERSION,
                                                                                          available_versions))


def main():
    """
    Get code from GitHub and perform an incremental build.
    Assumes that the required SDKs directory is called 'SDKs' and is directly adjacent to the repo checkout directory.
    """
    repository = USED_REPOSITORY
    branch = USED_BRANCH
    target = USED_TARGET
    config = USED_CONFIG
    build_dir = '_'.join([target, config.lower()])

    steps = {
        'clone': ['git', 'clone', 'https://github.com/CRYTEK-CRYENGINE/{repo}.git'.format(repo=repository)],
        'pull': ['git', '-C', repository, 'pull'],
        'checkout': ['git', 'checkout', branch],

        # Quietly remove files that aren't tracked by git but leave the build folder in place (for incremental builds).
        'clean': ['git', 'clean', '-dfq', '-e', 'Code/SDKs', '-e', build_dir],

        # For now, assume Windows for convenience.
        'configure': ['cmake', r'-DCMAKE_TOOLCHAIN_FILE=Tools\CMake\toolchain\windows\WindowsPC-MSVC.cmake', '..'],
        'build': [os.path.normpath(r'C:\Program Files (x86)\MSBuild\{}\Bin\MSBuild.exe'.format(USED_VS_VERSION)),
                  '/property:Configuration={}'.format(config),
                  'CryEngine_CMake_{}.sln'.format(TARGET_TO_SLN_TAG.get(target))]
    }

    if os.path.exists(repository):
        runstep(steps, 'pull')
    else:
        runstep(steps, 'clone')

    os.chdir(repository)
    runstep(steps, 'checkout')

    runstep(steps, 'clean')

    if os.path.exists(os.path.join('Code', 'SDKs')):
        if platform.system() == 'Windows':
            subprocess.check_call(['rmdir', r'Code\SDKs'], shell=True)

    if not os.path.exists(os.path.join('Code', 'SDKs')):
        if platform.system() == 'Windows':
            subprocess.check_call(['mklink', '/J', r'Code\SDKs', r'..\SDKs'], shell=True)

    print('Changing to build directory: {}'.format(build_dir))
    if not os.path.exists(build_dir):
        os.mkdir(build_dir)
    os.chdir(build_dir)
    runstep(steps, 'configure')
    runstep(steps, 'build')
    os.chdir('..')

    if platform.system() == 'Windows':
        subprocess.check_call(['rmdir', r'Code\SDKs'], shell=True)
    runstep(steps, 'clean')


def runstep(steps, name):
    """
    Run the command from *steps* corresponding to *name*.
    :param steps: Dictionary of steps that can be run.
    :param name: Name of the step to run.
    """
    print('Running {} step with command "{}".'.format(name, ' '.join(steps[name])))
    subprocess.check_call(steps[name])


if __name__ == '__main__':
    main()
