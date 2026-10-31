"""과제가 요구하는 실행 명령(python main.py)을 패키지 진입점에 연결한다."""
import runpy

if __name__ == "__main__":
    runpy.run_module('gitgen', run_name="__main__", alter_sys=True)
