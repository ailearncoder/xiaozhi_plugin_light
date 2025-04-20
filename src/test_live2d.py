from thing.plugins.live2d import Live2D

if __name__ == "__main__":
    live_2d = Live2D()
    # live_2d.switch_model('Mao')
    print(live_2d.info())
    print(live_2d.start_motion('Idle', 0))
    print(live_2d.start_expression('exp_02'))
