import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeBackground({
  theme = 'dark',
  mode = 'idle',
  preset = 'lattice',
  speedMultiplier = 1.0,
  shockwaveTrigger = 0,
}) {
  const containerRef = useRef(null);
  const themeRef = useRef(theme);
  const modeRef = useRef(mode);
  const presetRef = useRef(preset);
  const speedRef = useRef(speedMultiplier);
  const shockwaveRef = useRef(shockwaveTrigger);

  useEffect(() => { themeRef.current = theme; }, [theme]);
  useEffect(() => { modeRef.current = mode; }, [mode]);
  useEffect(() => { presetRef.current = preset; }, [preset]);
  useEffect(() => { speedRef.current = speedMultiplier; }, [speedMultiplier]);

  // Handle shockwave impulses
  const addShockwaveImpulseRef = useRef(null);
  useEffect(() => {
    if (shockwaveTrigger > 0 && addShockwaveImpulseRef.current) {
      addShockwaveImpulseRef.current(0, 0); // shockwave at center canvas
    }
  }, [shockwaveTrigger]);

  useEffect(() => {
    if (!containerRef.current) return;

    // 1. Scene, Camera, Renderer Setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      1,
      2500
    );
    camera.position.set(0, 0, 520);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    containerRef.current.appendChild(renderer.domElement);

    // 2. Color Palettes (Dark / Light Theme Adaptability)
    const palettes = {
      dark: {
        primary: new THREE.Color(0x6366f1),    // Indigo
        secondary: new THREE.Color(0x06b6d4),  // Cyan
        accent: new THREE.Color(0xc084fc),     // Purple
        success: new THREE.Color(0x10b981),    // Emerald
        grid: new THREE.Color(0x1e1b4b),       // Deep Indigo Grid
        pointLight1: 0x818cf8,
        pointLight2: 0x06b6d4,
        lineOpacity: 0.25,
      },
      light: {
        primary: new THREE.Color(0x3b82f6),    // Blue
        secondary: new THREE.Color(0x8b5cf6),  // Violet
        accent: new THREE.Color(0xec4899),     // Pink
        success: new THREE.Color(0x059669),    // Green
        grid: new THREE.Color(0xdbeafe),       // Soft Sky Grid
        pointLight1: 0x3b82f6,
        pointLight2: 0x8b5cf6,
        lineOpacity: 0.18,
      },
    };

    let activePalette = themeRef.current === 'light' ? palettes.light : palettes.dark;

    // 3. Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
    scene.add(ambientLight);

    const leftLight = new THREE.PointLight(activePalette.pointLight1, 3.5, 900);
    leftLight.position.set(-360, 150, 300);
    scene.add(leftLight);

    const rightLight = new THREE.PointLight(activePalette.pointLight2, 3.5, 900);
    rightLight.position.set(360, -150, 300);
    scene.add(rightLight);

    // =========================================================================
    // 4. LEFT SIDE 3D STRUCTURE: QUANTUM CORE (X: -360)
    // =========================================================================
    const leftGroup = new THREE.Group();
    leftGroup.position.set(-360, 40, 0);

    // Left Outer Wireframe Icosahedron
    const leftCoreGeo = new THREE.IcosahedronGeometry(95, 2);
    const leftCoreMat = new THREE.MeshPhongMaterial({
      color: activePalette.primary,
      wireframe: true,
      transparent: true,
      opacity: 0.55,
      shininess: 90,
    });
    const leftCoreMesh = new THREE.Mesh(leftCoreGeo, leftCoreMat);
    leftGroup.add(leftCoreMesh);

    // Left Inner Quantum Octahedron
    const leftInnerGeo = new THREE.OctahedronGeometry(50, 1);
    const leftInnerMat = new THREE.MeshStandardMaterial({
      color: activePalette.secondary,
      wireframe: true,
      transparent: true,
      opacity: 0.75,
      metalness: 0.9,
      roughness: 0.1,
    });
    const leftInnerMesh = new THREE.Mesh(leftInnerGeo, leftInnerMat);
    leftGroup.add(leftInnerMesh);

    // Left Glowing Center Energy Orb
    const leftOrbGeo = new THREE.SphereGeometry(22, 32, 32);
    const leftOrbMat = new THREE.MeshBasicMaterial({
      color: activePalette.accent,
      transparent: true,
      opacity: 0.85,
    });
    const leftOrbMesh = new THREE.Mesh(leftOrbGeo, leftOrbMat);
    leftGroup.add(leftOrbMesh);

    // Left Torus Rings
    const leftRingGeo = new THREE.TorusGeometry(140, 1.2, 16, 100);
    const leftRingMat = new THREE.MeshBasicMaterial({
      color: activePalette.secondary,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const leftRingMesh = new THREE.Mesh(leftRingGeo, leftRingMat);
    leftRingMesh.rotation.x = Math.PI / 3;
    leftGroup.add(leftRingMesh);

    scene.add(leftGroup);

    // =========================================================================
    // 5. RIGHT SIDE 3D STRUCTURE: HOLOGRAPHIC SECURITY SHIELD CORE (X: +360)
    // =========================================================================
    const rightGroup = new THREE.Group();
    rightGroup.position.set(360, 40, 0);

    // Right Outer Wireframe Dodecahedron
    const rightCoreGeo = new THREE.DodecahedronGeometry(95, 1);
    const rightCoreMat = new THREE.MeshPhongMaterial({
      color: activePalette.secondary,
      wireframe: true,
      transparent: true,
      opacity: 0.55,
      shininess: 90,
    });
    const rightCoreMesh = new THREE.Mesh(rightCoreGeo, rightCoreMat);
    rightGroup.add(rightCoreMesh);

    // Right Inner Tetrahedral Reactor
    const rightInnerGeo = new THREE.TetrahedronGeometry(55, 1);
    const rightInnerMat = new THREE.MeshStandardMaterial({
      color: activePalette.accent,
      wireframe: true,
      transparent: true,
      opacity: 0.75,
      metalness: 0.85,
      roughness: 0.15,
    });
    const rightInnerMesh = new THREE.Mesh(rightInnerGeo, rightInnerMat);
    rightGroup.add(rightInnerMesh);

    // Right Glowing Center Orb
    const rightOrbGeo = new THREE.SphereGeometry(22, 32, 32);
    const rightOrbMat = new THREE.MeshBasicMaterial({
      color: activePalette.primary,
      transparent: true,
      opacity: 0.85,
    });
    const rightOrbMesh = new THREE.Mesh(rightOrbGeo, rightOrbMat);
    rightGroup.add(rightOrbMesh);

    // Right Laser Torus Ring
    const rightRingGeo = new THREE.TorusKnotGeometry(125, 0.7, 120, 16);
    const rightRingMat = new THREE.MeshBasicMaterial({
      color: activePalette.accent,
      wireframe: true,
      transparent: true,
      opacity: 0.28,
    });
    const rightRingMesh = new THREE.Mesh(rightRingGeo, rightRingMat);
    rightGroup.add(rightRingMesh);

    scene.add(rightGroup);

    // =========================================================================
    // 6. 3D SCANNING LASER PLANE (Active during Scanning Mode)
    // =========================================================================
    const scanPlaneGeo = new THREE.PlaneGeometry(1200, 4);
    const scanPlaneMat = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.0, // hidden by default
      side: THREE.DoubleSide,
    });
    const scanPlaneMesh = new THREE.Mesh(scanPlaneGeo, scanPlaneMat);
    scanPlaneMesh.position.set(0, 0, 80);
    scene.add(scanPlaneMesh);

    // =========================================================================
    // 7. CENTER & MIDDLE: 3D CYBER WAVE GRID (Bottom Data Floor)
    // =========================================================================
    const gridWidth = 1100;
    const gridHeight = 700;
    const gridSegs = 40;
    const waveGeo = new THREE.PlaneGeometry(gridWidth, gridHeight, gridSegs, gridSegs);
    waveGeo.rotateX(-Math.PI / 2.2);

    const waveMat = new THREE.MeshBasicMaterial({
      color: activePalette.grid,
      wireframe: true,
      transparent: true,
      opacity: 0.32,
    });
    const waveMesh = new THREE.Mesh(waveGeo, waveMat);
    waveMesh.position.y = -220;
    scene.add(waveMesh);

    // =========================================================================
    // 8. PARTICLE CONSTELLATION MATRIX & SHOCKWAVE SYSTEM
    // =========================================================================
    const particleCount = 240;
    const particleGeo = new THREE.BufferGeometry();
    const pPositions = new Float32Array(particleCount * 3);
    const pVelocities = [];

    for (let i = 0; i < particleCount; i++) {
      const x = (Math.random() - 0.5) * 1100;
      const y = (Math.random() - 0.5) * 800;
      const z = (Math.random() - 0.5) * 450;

      pPositions[i * 3] = x;
      pPositions[i * 3 + 1] = y;
      pPositions[i * 3 + 2] = z;

      pVelocities.push({
        x: (Math.random() - 0.5) * 0.45,
        y: (Math.random() - 0.5) * 0.45,
        z: (Math.random() - 0.5) * 0.3,
        vx: 0,
        vy: 0,
        vz: 0,
      });
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: activePalette.primary,
      size: 4.8,
      transparent: true,
      opacity: 0.85,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // Connecting Lines
    const lineMat = new THREE.LineBasicMaterial({
      color: activePalette.secondary,
      transparent: true,
      opacity: activePalette.lineOpacity,
    });
    const lineGeo = new THREE.BufferGeometry();
    const lineMesh = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lineMesh);

    // Orbiting Floating Geometric Data Nodes
    const nodeCount = 14;
    const floatingNodes = [];
    for (let i = 0; i < nodeCount; i++) {
      const geom = i % 2 === 0
        ? new THREE.BoxGeometry(11, 11, 11)
        : new THREE.TetrahedronGeometry(9);

      const mat = new THREE.MeshBasicMaterial({
        color: i % 2 === 0 ? activePalette.secondary : activePalette.accent,
        wireframe: true,
        transparent: true,
        opacity: 0.65,
      });

      const mesh = new THREE.Mesh(geom, mat);
      const isLeftNode = i < nodeCount / 2;
      const centerX = isLeftNode ? -360 : 360;
      const angle = (i / nodeCount) * Math.PI * 4;
      const radius = 160 + Math.random() * 60;

      mesh.position.x = centerX + Math.cos(angle) * radius;
      mesh.position.y = (Math.random() - 0.5) * 220;
      mesh.position.z = Math.sin(angle) * radius;

      scene.add(mesh);
      floatingNodes.push({
        mesh,
        angle,
        radius,
        centerX,
        speed: 0.006 + Math.random() * 0.008,
        rotSpeedX: 0.02 + Math.random() * 0.02,
        rotSpeedY: 0.02 + Math.random() * 0.02,
        yBase: mesh.position.y,
      });
    }

    // Shockwave Rings Array for Mouse Clicks / Impulses
    const shockwaves = [];
    const createShockwave = (x, y) => {
      const ringGeo = new THREE.RingGeometry(5, 8, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: activePalette.accent,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.9,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.set(x, y, 50);
      scene.add(ringMesh);
      shockwaves.push({ mesh: ringMesh, scale: 1, maxScale: 45, opacity: 0.9 });
    };

    addShockwaveImpulseRef.current = createShockwave;

    // =========================================================================
    // 9. MOUSE INTERACTION & RAYCASTING
    // =========================================================================
    let mouseX = 0;
    let mouseY = 0;
    const raycaster = new THREE.Raycaster();
    const mouseVector = new THREE.Vector2(-999, -999);

    const handleMouseMove = (e) => {
      mouseX = (e.clientX - window.innerWidth / 2);
      mouseY = (e.clientY - window.innerHeight / 2);

      mouseVector.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouseVector.y = -(e.clientY / window.innerHeight) * 2 + 1;
    };

    const handleCanvasClick = (e) => {
      // Raycast click position into 3D world space
      raycaster.setFromCamera(mouseVector, camera);
      const targetZ = 0;
      const distanceZ = (targetZ - camera.position.z) / raycaster.ray.direction.z;
      const click3D = camera.position.clone().add(raycaster.ray.direction.clone().multiplyScalar(distanceZ));

      createShockwave(click3D.x, click3D.y);

      // Trigger particle impulse explosion outward from click coordinate
      const pArr = particleGeo.attributes.position.array;
      for (let i = 0; i < particleCount; i++) {
        const dx = pArr[i * 3] - click3D.x;
        const dy = pArr[i * 3 + 1] - click3D.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 260 && dist > 0) {
          const force = (1 - dist / 260) * 18;
          pVelocities[i].vx += (dx / dist) * force;
          pVelocities[i].vy += (dy / dist) * force;
        }
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('click', handleCanvasClick);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    // =========================================================================
    // 10. ANIMATION LOOP
    // =========================================================================
    let animationFrameId;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const elapsed = clock.getElapsedTime();
      const speed = speedRef.current;
      const currentMode = modeRef.current;
      const currentPreset = presetRef.current;

      // Theme Colors Smooth Interpolation (lerp)
      const targetPalette = themeRef.current === 'light' ? palettes.light : palettes.dark;
      leftCoreMat.color.lerp(currentMode === 'secured' ? targetPalette.success : targetPalette.primary, 0.05);
      rightCoreMat.color.lerp(currentMode === 'secured' ? targetPalette.success : targetPalette.secondary, 0.05);
      leftInnerMat.color.lerp(targetPalette.secondary, 0.05);
      rightInnerMat.color.lerp(targetPalette.accent, 0.05);
      leftOrbMat.color.lerp(targetPalette.accent, 0.05);
      rightOrbMat.color.lerp(targetPalette.primary, 0.05);
      particleMat.color.lerp(targetPalette.primary, 0.05);
      lineMat.color.lerp(targetPalette.secondary, 0.05);
      waveMat.color.lerp(targetPalette.grid, 0.05);
      leftLight.color.lerp(new THREE.Color(targetPalette.pointLight1), 0.05);
      rightLight.color.lerp(new THREE.Color(targetPalette.pointLight2), 0.05);

      // Mode-dependent rotation boost
      const modeSpeedBoost = currentMode === 'scanning' ? 2.6 : 1.0;
      const totalSpeed = speed * modeSpeedBoost;

      // A. Animate Left & Right 3D Visual Cores
      if (currentPreset === 'lattice' || currentPreset === 'vortex' || currentPreset === 'shield') {
        leftGroup.visible = true;
        rightGroup.visible = true;

        leftCoreMesh.rotation.x = elapsed * 0.15 * totalSpeed;
        leftCoreMesh.rotation.y = elapsed * 0.22 * totalSpeed;
        leftInnerMesh.rotation.x = -elapsed * 0.3 * totalSpeed;
        leftInnerMesh.rotation.z = elapsed * 0.25 * totalSpeed;
        leftRingMesh.rotation.z = elapsed * 0.18 * totalSpeed;

        rightCoreMesh.rotation.x = -elapsed * 0.18 * totalSpeed;
        rightCoreMesh.rotation.y = elapsed * 0.25 * totalSpeed;
        rightInnerMesh.rotation.y = elapsed * 0.32 * totalSpeed;
        rightRingMesh.rotation.y = elapsed * 0.2 * totalSpeed;

        const pulseScale = 1 + Math.sin(elapsed * 3 * totalSpeed) * 0.12;
        leftOrbMesh.scale.set(pulseScale, pulseScale, pulseScale);
        rightOrbMesh.scale.set(pulseScale, pulseScale, pulseScale);
      } else {
        leftGroup.visible = false;
        rightGroup.visible = false;
      }

      // B. Animate 3D Laser Scanning Plane (Scanning Mode)
      if (currentMode === 'scanning') {
        scanPlaneMat.opacity = 0.55 + Math.sin(elapsed * 6) * 0.2;
        scanPlaneMesh.position.y = Math.sin(elapsed * 2.5 * speed) * 260;
      } else {
        scanPlaneMat.opacity = 0.0;
      }

      // C. Animate 3D Cyber Wave Grid Floor
      const wPos = waveGeo.attributes.position;
      for (let i = 0; i < wPos.count; i++) {
        const u = i % (gridSegs + 1);
        const v = Math.floor(i / (gridSegs + 1));
        const zWave = Math.sin(elapsed * 2 * totalSpeed + u * 0.35 + v * 0.25) * 14
                    + Math.cos(elapsed * 1.6 * totalSpeed + u * 0.2) * 9;
        wPos.setZ(i, zWave);
      }
      wPos.needsUpdate = true;

      // D. Animate Orbiting Data Nodes
      floatingNodes.forEach((node) => {
        node.angle += node.speed * totalSpeed;
        node.mesh.position.x = node.centerX + Math.cos(node.angle) * node.radius;
        node.mesh.position.z = Math.sin(node.angle) * node.radius;
        node.mesh.position.y = node.yBase + Math.sin(elapsed * 2 * totalSpeed + node.angle) * 20;
        node.mesh.rotation.x += node.rotSpeedX * totalSpeed;
        node.mesh.rotation.y += node.rotSpeedY * totalSpeed;
      });

      // E. Animate Particles & Shockwaves
      const pArr = particleGeo.attributes.position.array;
      const linePositions = [];

      // Convert 2D mouse position to 3D plane projection for particle force field
      raycaster.setFromCamera(mouseVector, camera);
      const targetZ = 0;
      const distZ = (targetZ - camera.position.z) / raycaster.ray.direction.z;
      const mouse3D = camera.position.clone().add(raycaster.ray.direction.clone().multiplyScalar(distZ));

      for (let i = 0; i < particleCount; i++) {
        pArr[i * 3] += pVelocities[i].x * totalSpeed;
        pArr[i * 3 + 1] += pVelocities[i].y * totalSpeed;
        pArr[i * 3 + 2] += pVelocities[i].z * totalSpeed;

        // Boundary rebound
        if (Math.abs(pArr[i * 3]) > 550) pVelocities[i].x *= -1;
        if (Math.abs(pArr[i * 3 + 1]) > 420) pVelocities[i].y *= -1;
        if (Math.abs(pArr[i * 3 + 2]) > 280) pVelocities[i].z *= -1;

        // Mouse Repulsion Force Field
        const dx = pArr[i * 3] - mouse3D.x;
        const dy = pArr[i * 3 + 1] - mouse3D.y;
        const distToMouse = Math.sqrt(dx * dx + dy * dy);

        const repulsionRadius = 150;
        if (distToMouse < repulsionRadius && distToMouse > 0) {
          const force = (1 - distToMouse / repulsionRadius) * 4.0;
          pVelocities[i].vx += (dx / distToMouse) * force;
          pVelocities[i].vy += (dy / distToMouse) * force;
        }

        // Apply velocity dampening
        pArr[i * 3] += pVelocities[i].vx;
        pArr[i * 3 + 1] += pVelocities[i].vy;
        pVelocities[i].vx *= 0.92;
        pVelocities[i].vy *= 0.92;

        // Connect nearby particles with lines
        for (let j = i + 1; j < particleCount; j++) {
          const ldx = pArr[i * 3] - pArr[j * 3];
          const ldy = pArr[i * 3 + 1] - pArr[j * 3 + 1];
          const ldz = pArr[i * 3 + 2] - pArr[j * 3 + 2];
          const pDist = Math.sqrt(ldx * ldx + ldy * ldy + ldz * ldz);

          if (pDist < 125) {
            linePositions.push(
              pArr[i * 3], pArr[i * 3 + 1], pArr[i * 3 + 2],
              pArr[j * 3], pArr[j * 3 + 1], pArr[j * 3 + 2]
            );
          }
        }
      }

      particleGeo.attributes.position.needsUpdate = true;
      lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));

      // Expand & Fade Shockwave Rings
      for (let i = shockwaves.length - 1; i >= 0; i--) {
        const sw = shockwaves[i];
        sw.scale += 0.8 * totalSpeed;
        sw.opacity -= 0.02 * totalSpeed;
        sw.mesh.scale.set(sw.scale, sw.scale, 1);
        sw.mesh.material.opacity = Math.max(0, sw.opacity);

        if (sw.opacity <= 0) {
          scene.remove(sw.mesh);
          shockwaves.splice(i, 1);
        }
      }

      // F. Smooth Camera Parallax Response
      const targetCamX = mouseX * 0.28;
      const targetCamY = mouseY * 0.28;

      camera.position.x += (targetCamX - camera.position.x) * 0.04;
      camera.position.y += (-targetCamY - camera.position.y) * 0.04;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('click', handleCanvasClick);
      window.removeEventListener('resize', handleResize);
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
      }}
    />
  );
}
