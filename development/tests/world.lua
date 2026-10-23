-- Current-engine regression: create_camera takes cm and direct downward degrees.
-- No renderer is mocked into claiming visual success; this checks inputs only.
local cameras,points,units={},{},{}
local bounds=6400
log={info=function()end}
package.loaded['spirit.effects']={new=function()return {}end}
local area={get_min_x=function()return -bounds end,get_max_x=function()return bounds end,
    get_min_y=function()return -bounds end,get_max_y=function()return bounds end,set_visible=function()end}
local function noop()end
y3={area={get_map_area=function()return area end},player={get_by_id=function(id)return id end},
    point={create=function(x,y,z)local p={x=x,y=y,z=z};points[#points+1]=p;return p end},
    unit={create_unit=function(owner,key,point)
        local unit={owner=owner,key=key,point=point,is_exist=function()return true end,
            add_state=noop,set_attr=noop,set_unit_scale=noop,set_name=noop,set_name_show_type=noop}
        units[#units+1]=unit;return unit
    end},camera={disable_camera_move=noop,create_camera=function(point,distance,height,yaw,pitch,fov)
        assert(distance>1000 and distance<10000,'camera input must remain in centimetres')
        assert(fov>=30 and fov<=60,'last argument is FOV, not far clipping distance')
        assert(pitch>=45 and pitch<=80,'direct downward pitch must not clamp to a top-down view')
        local camera={point=point,distance=distance,height=height,yaw=yaw,pitch=pitch,fov=fov,apply=noop}
        cameras[#cameras+1]=camera;return camera
    end}}
local World=require 'spirit.world'
local assets={floor=1,pad=2,gate=3}
for _,case in ipairs({{ids={1},bounds=6400},{ids={1,2,3,4},bounds=4000}}) do
    bounds=case.bounds;cameras={};points={};units={}
    local world=World.new({player_order=case.ids},assets)
    assert(#cameras==#case.ids and #units==82*#case.ids)
    for index,id in ipairs(case.ids) do
        local camera=cameras[index]
        local scale=world.scale
        local lane=world.lanes[id]
        assert(math.abs(camera.point.x-lane.x)<.001)
        assert(camera.point.y<lane.y,'focus must leave room below the battlefield')
        assert(camera.distance==6500*scale,'scaled lane camera must preserve the native-tested distance')
        assert(camera.pitch==65 and camera.fov==40,'preserve native-tested pitch and FOV')
        world:focus(id)
    end
end
print('PASS world camera cm/direct-pitch contract and scaled multiplayer lanes (not rendered)')
